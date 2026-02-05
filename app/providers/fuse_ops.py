import os
import stat
import errno
import time
import logging
import threading
from typing import Dict, Any, Optional, List

import httpx
try:
    from fuse import Operations, FuseOSError, LoggingMixIn, FUSE
    HAS_FUSE = True
except (ImportError, OSError, EnvironmentError):
    # Fallback for environments without FUSE
    class Operations: pass
    class LoggingMixIn: pass
    class FuseOSError(Exception): pass
    FUSE = None
    HAS_FUSE = False

from p115client import P115Client

# 配置日志
logger = logging.getLogger("strm_fuse")

class P115FuseOperations(LoggingMixIn, Operations):
    """
    115 网盘 FUSE 操作实现 (同步模式)
    """

    def __init__(self, cookie_file: str, mount_point: str, root_cid: str = "0"):
        self.cookie_file = cookie_file
        self.mount_point = mount_point
        self.root_cid = root_cid
        # 读取 cookie 文件并解析
        cookies = self._load_cookies(cookie_file)
        # 使用 p115client，check_for_relogin=True 会自动刷新 cookie
        self.client = P115Client(cookies, check_for_relogin=True)

        # 缓存配置
        self.cache_ttl = 60  # 缓存有效期 60 秒
        self.attr_cache: Dict[str, Any] = {}  # path -> (st, expire_time)
        self.children_cache: Dict[str, Any] = {}  # path -> ([names], expire_time)

        # 路径映射: path -> file_info
        # file_info 结构: {'id': str, 'name': str, 'is_dir': bool, 'size': int, 'time': int, 'pick_code': str}
        self.file_map: Dict[str, Any] = {'/': {'id': root_cid, 'is_dir': True}}

        # 文件描述符映射: fd -> {'info': file_info, 'url': str}
        self.fd_map: Dict[int, Any] = {}
        self.fd_counter = 1000

        self._lock = threading.Lock()

        # 用户/组 ID
        self.uid = os.getuid()
        self.gid = os.getgid()

        # HTTP 客户端用于下载
        self.http_client = httpx.Client(follow_redirects=True, timeout=30.0)

    def _load_cookies(self, cookie_file: str) -> dict:
        """从文件加载 cookie 并解析为字典"""
        try:
            with open(cookie_file, 'r', encoding='latin-1') as f:
                cookie_str = f.read().strip()
            # 解析 cookie 字符串，格式: "key1=value1; key2=value2"
            cookies = {}
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
            return cookies
        except Exception as e:
            logger.error(f"Failed to load cookies from {cookie_file}: {e}")
            raise

    def __del__(self):
        try:
            self.http_client.close()
        except:
            pass

    def _get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        with self._lock:
            return self.file_map.get(path)

    def _add_to_cache(self, path: str, info: Dict[str, Any]):
        """添加文件信息到缓存"""
        with self._lock:
            self.file_map[path] = info

    def getattr(self, path: str, fh=None):
        """获取文件属性"""
        # 检查缓存
        with self._lock:
            if path in self.attr_cache:
                st, expire = self.attr_cache[path]
                if time.time() < expire:
                    return st

        info = self._get_file_info(path)

        # 根目录特殊处理
        if path == '/':
            st = {
                'st_mode': (stat.S_IFDIR | 0o755),
                'st_nlink': 2,
                'st_size': 0,
                'st_ctime': time.time(),
                'st_mtime': time.time(),
                'st_atime': time.time(),
                'st_uid': self.uid,
                'st_gid': self.gid
            }
        elif info:
            is_dir = info.get('is_dir', False)
            mode = (stat.S_IFDIR | 0o755) if is_dir else (stat.S_IFREG | 0o644)
            size = info.get('size', 0)
            timestamp = info.get('time', time.time())

            st = {
                'st_mode': mode,
                'st_nlink': 2 if is_dir else 1,
                'st_size': size,
                'st_ctime': timestamp,
                'st_mtime': timestamp,
                'st_atime': time.time(),
                'st_uid': self.uid,
                'st_gid': self.gid
            }
        else:
            # 尝试刷新父目录以查找该文件
            parent = os.path.dirname(path)
            if parent == path: # 应该是根目录，但已经处理过了
                raise FuseOSError(errno.ENOENT)

            # 检查父目录是否已知且为目录
            parent_info = self._get_file_info(parent)
            if parent_info and parent_info.get('is_dir'):
                # 刷新父目录
                self._refresh_dir(parent, parent_info['id'])
                # 再次检查
                info = self._get_file_info(path)
                if info:
                    is_dir = info.get('is_dir', False)
                    mode = (stat.S_IFDIR | 0o755) if is_dir else (stat.S_IFREG | 0o644)
                    size = info.get('size', 0)
                    timestamp = info.get('time', time.time())
                    st = {
                        'st_mode': mode,
                        'st_nlink': 2 if is_dir else 1,
                        'st_size': size,
                        'st_ctime': timestamp,
                        'st_mtime': timestamp,
                        'st_atime': time.time(),
                        'st_uid': self.uid,
                        'st_gid': self.gid
                    }
                else:
                    raise FuseOSError(errno.ENOENT)
            else:
                raise FuseOSError(errno.ENOENT)

        # 更新缓存
        with self._lock:
            self.attr_cache[path] = (st, time.time() + self.cache_ttl)

        return st

    def _refresh_dir(self, path: str, cid: str) -> List[str]:
        """刷新目录缓存"""
        try:
            # 同步调用 p115client
            # 注意：p115client 的 fs_files 默认 limit 较小，这里需要分页获取所有文件
            # 为了简化，先获取前 10000 个，这通常够用了
            resp = self.client.fs_files(cid, limit=10000)

            if not resp.get('state'):
                logger.error(f"Failed to list files for cid {cid}: {resp.get('error')}")
                return []

            files = resp.get('data', [])
            names = []

            for item in files:
                name = item.get('n')
                if not name:
                    continue

                child_path = os.path.join(path, name) if path != '/' else f"/{name}"
                names.append(name)

                # 解析文件信息
                # fc: 0=文件夹, 1=视频, ...
                is_dir = False
                fc = item.get('fc')
                if fc is not None:
                    is_dir = int(fc) == 0
                else:
                    is_dir = not bool(item.get('sha'))

                file_info = {
                    'id': str(item.get('cid')),
                    'name': name,
                    'is_dir': is_dir,
                    'size': int(item.get('s', 0)),
                    'pick_code': item.get('pc', ''),
                    'time': int(item.get('t', 0))
                }

                self._add_to_cache(child_path, file_info)

            return names
        except Exception as e:
            logger.exception(f"Error listing dir {cid}: {e}")
            return []

    def readdir(self, path: str, fh):
        """读取目录"""
        # 检查缓存
        with self._lock:
            if path in self.children_cache:
                names, expire = self.children_cache[path]
                if time.time() < expire:
                    return ['.', '..'] + names

        info = self._get_file_info(path)
        if not info or not info.get('is_dir'):
            raise FuseOSError(errno.ENOTDIR)

        names = self._refresh_dir(path, info['id'])

        with self._lock:
            self.children_cache[path] = (names, time.time() + self.cache_ttl)

        return ['.', '..'] + names

    def open(self, path: str, flags):
        """打开文件"""
        info = self._get_file_info(path)
        if not info:
            raise FuseOSError(errno.ENOENT)

        if info.get('is_dir'):
            raise FuseOSError(errno.EISDIR)

        try:
            pick_code = info.get('pick_code')
            if not pick_code:
                # 尝试获取 pick_code
                file_id = int(info['id'])
                pick_code = self.client.to_pickcode(file_id)
                info['pick_code'] = pick_code

            # 获取下载链接
            # 指定 app='chrome' 以获得通用的下载链接
            download_url = self.client.download_url(pick_code, app='chrome')

            with self._lock:
                fd = self.fd_counter
                self.fd_counter += 1
                self.fd_map[fd] = {
                    'info': info,
                    'url': download_url
                }
            return fd

        except Exception as e:
            logger.error(f"Error opening file {path}: {e}")
            raise FuseOSError(errno.EIO)

    def read(self, path: str, size: int, offset: int, fh):
        """读取文件内容"""
        with self._lock:
            if fh not in self.fd_map:
                raise FuseOSError(errno.EBADF)
            fd_data = self.fd_map[fh]

        url = fd_data['url']
        info = fd_data['info']

        # 文件总大小
        file_size = info.get('size', 0)
        if offset >= file_size:
            return b""

        # 调整读取大小，防止越界
        if offset + size > file_size:
            size = file_size - offset

        # 使用 Range 头请求数据
        headers = {
            'Range': f'bytes={offset}-{offset + size - 1}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            resp = self.http_client.get(url, headers=headers)

            if resp.status_code in (200, 206):
                return resp.content

            elif resp.status_code == 403:
                # 链接可能过期，刷新链接
                logger.info(f"Link expired for {path}, refreshing...")
                pick_code = info['pick_code']
                new_url = self.client.download_url(pick_code, app='chrome')

                with self._lock:
                    if fh in self.fd_map:
                        self.fd_map[fh]['url'] = new_url

                # 重试
                resp = self.http_client.get(new_url, headers=headers)
                if resp.status_code in (200, 206):
                    return resp.content

            logger.error(f"Read failed with status {resp.status_code}")
            raise FuseOSError(errno.EIO)

        except Exception as e:
            logger.error(f"Read error: {e}")
            raise FuseOSError(errno.EIO)

    def release(self, path: str, fh):
        """关闭文件"""
        with self._lock:
            if fh in self.fd_map:
                del self.fd_map[fh]
        return 0
