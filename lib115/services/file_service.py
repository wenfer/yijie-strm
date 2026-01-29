"""
115 网盘文件服务模块
提供文件遍历、路径解析、下载链接缓存等高级功能
"""
from __future__ import annotations
import logging
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable, Any

from ..api.client import Client115, is_folder, get_item_attr
from ..config import AppConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    expire_at: float


class DownloadUrlCache:
    """下载链接缓存"""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        """获取缓存的下载链接"""
        with self._lock:
            entry = self._cache.get(key)
            if entry and time.time() < entry.expire_at:
                return entry.value
            elif entry:
                del self._cache[key]
            return None

    def set(self, key: str, value: str):
        """设置下载链接缓存"""
        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                expire_at=time.time() + self.ttl
            )

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def cleanup(self):
        """清理过期缓存"""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if now >= v.expire_at]
            for k in expired:
                del self._cache[k]


class FileService:
    """文件服务 - 提供高级文件操作功能"""

    def __init__(self, client: Client115 = None, config: AppConfig = None):
        self.config = config or default_config
        self.client = client or Client115(self.config)
        self._url_cache = DownloadUrlCache(ttl=self.config.gateway.CACHE_TTL)

    def close(self):
        """关闭服务"""
        if hasattr(self, '_owns_client') and self._owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 下载链接服务 ====================

    def get_download_url(self, pick_code: str, use_cache: bool = True) -> Optional[str]:
        """获取下载链接（支持缓存）"""
        if use_cache:
            cached = self._url_cache.get(pick_code)
            if cached:
                logger.debug(f"Cache hit for pick_code: {pick_code}")
                return cached

        url = self.client.get_download_url(pick_code)
        if url and use_cache:
            self._url_cache.set(pick_code, url)

        return url

    def get_download_url_from_item(self, item: Dict, use_cache: bool = True) -> Optional[str]:
        """从文件项获取下载链接"""
        pick_code = get_item_attr(item, "pc", "pick_code")
        if not pick_code:
            return None
        return self.get_download_url(pick_code, use_cache)

    # ==================== 文件遍历服务 ====================

    def traverse_folder(
        self,
        root_cid: str,
        root_name: str = "",
        item_handler: Callable[[Dict], None] = None,
        folder_handler: Callable[[Dict], None] = None,
        max_depth: int = -1
    ) -> List[Dict]:
        """
        BFS 并发遍历文件夹

        Args:
            root_cid: 根目录 CID
            root_name: 根目录名称
            item_handler: 文件处理回调
            folder_handler: 文件夹处理回调
            max_depth: 最大遍历深度，-1 表示无限制

        Returns:
            所有遍历到的项目列表
        """
        all_items = []
        all_items_lock = threading.Lock()
        visited = set()
        visited_lock = threading.Lock()

        # 任务队列: (cid, name, parent_path, depth)
        task_queue = deque()
        task_queue.append((root_cid, root_name, "", 0))

        with visited_lock:
            visited.add(root_cid)

        def _process_directory(cid: str, name: str, parent_path: str, depth: int):
            """处理单个目录"""
            try:
                items = self.client.list_all_files(cid)
                if not items:
                    return [], []

                current_path = os.path.join(parent_path, name).replace("\\", "/") if parent_path else name
                processed_items = []
                subdirs = []

                for item in items:
                    item_copy = item.copy()
                    item_name = get_item_attr(item, "fn", "file_name", default="Unknown")
                    rel_path = os.path.join(current_path, item_name).replace("\\", "/")
                    item_copy["_relative_path"] = rel_path
                    item_copy["_depth"] = depth
                    processed_items.append(item_copy)

                    if is_folder(item):
                        fid = get_item_attr(item, "fid", "file_id")
                        if fid:
                            subdirs.append((fid, item_name))

                return processed_items, subdirs

            except Exception as e:
                logger.error(f"Error processing directory CID {cid}: {e}")
                return [], []

        with ThreadPoolExecutor(max_workers=self.config.network.API_CONCURRENT_THREADS) as executor:
            futures = {}

            while task_queue or futures:
                # 提交新任务
                while task_queue and len(futures) < self.config.network.API_CONCURRENT_THREADS:
                    cid, name, parent_path, depth = task_queue.popleft()
                    if max_depth >= 0 and depth > max_depth:
                        continue
                    future = executor.submit(_process_directory, cid, name, parent_path, depth)
                    futures[future] = (cid, name, parent_path, depth)

                if not futures:
                    break

                # 处理完成的任务
                for future in as_completed(futures):
                    cid, name, parent_path, depth = futures.pop(future)
                    try:
                        items, subdirs = future.result()
                    except Exception as e:
                        logger.error(f"Future for CID {cid} raised exception: {e}")
                        items, subdirs = [], []

                    # 收集结果
                    if items:
                        with all_items_lock:
                            for item in items:
                                all_items.append(item)
                                if is_folder(item):
                                    if folder_handler:
                                        folder_handler(item)
                                else:
                                    if item_handler:
                                        item_handler(item)

                    # 添加子目录任务
                    if max_depth < 0 or depth < max_depth:
                        for sub_cid, sub_name in subdirs:
                            with visited_lock:
                                if sub_cid not in visited:
                                    visited.add(sub_cid)
                                    new_path = os.path.join(parent_path, name).replace("\\", "/") if parent_path else name
                                    task_queue.append((sub_cid, sub_name, new_path, depth + 1))

                    break  # 只处理一个完成的任务，立即去提交新任务

        return all_items

    # ==================== 路径解析服务 ====================

    def get_item_path(self, file_id: str) -> Optional[str]:
        """获取文件/文件夹的完整路径"""
        info = self.client.get_item_info(file_id)
        if not info:
            return None

        paths = info.get("paths", [])
        if not paths:
            return None

        path_parts = [get_item_attr(p, "file_name", default="") for p in paths if get_item_attr(p, "file_name")]
        item_name = info.get("file_name", "")
        if item_name:
            path_parts.append(item_name)

        return "/" + "/".join(path_parts) if path_parts else "/"

    def resolve_path(self, path: str, start_cid: str = '0') -> Optional[Dict]:
        """
        解析路径到文件/文件夹项

        Args:
            path: 路径字符串，如 "/电影/科幻/xxx.mkv"
            start_cid: 起始目录 CID

        Returns:
            找到的文件/文件夹项，未找到返回 None
        """
        path = path.strip("/")
        if not path:
            return {"fid": start_cid, "fn": "Root", "fc": "0"}

        parts = path.split("/")
        current_cid = start_cid

        for i, part in enumerate(parts):
            items, _ = self.client.list_files(current_cid, limit=self.config.API_FETCH_LIMIT)
            found = None

            for item in items:
                item_name = get_item_attr(item, "fn", "file_name")
                if item_name == part:
                    found = item
                    break

            if not found:
                logger.warning(f"Path component not found: {part}")
                return None

            if i < len(parts) - 1:
                # 中间路径必须是文件夹
                if not is_folder(found):
                    logger.warning(f"Path component is not a folder: {part}")
                    return None
                current_cid = get_item_attr(found, "fid", "file_id")
            else:
                return found

        return None

    # ==================== 文件统计服务 ====================

    def get_folder_stats(self, cid: str) -> Dict:
        """
        获取文件夹统计信息

        Returns:
            {
                "total_files": int,
                "total_folders": int,
                "total_size": int,
                "file_types": Dict[str, int]
            }
        """
        stats = {
            "total_files": 0,
            "total_folders": 0,
            "total_size": 0,
            "file_types": {}
        }

        def _count_item(item):
            if is_folder(item):
                stats["total_folders"] += 1
            else:
                stats["total_files"] += 1
                size = get_item_attr(item, "fs", "file_size", default=0)
                try:
                    stats["total_size"] += int(size)
                except (ValueError, TypeError):
                    pass

                # 统计文件类型
                name = get_item_attr(item, "fn", "file_name", default="")
                ext = os.path.splitext(name)[1].lower()
                if ext:
                    stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1

        self.traverse_folder(cid, "", item_handler=_count_item, folder_handler=_count_item)
        return stats


class FileIndex:
    """文件索引 - 用于快速查找文件"""

    def __init__(self):
        self._by_id: Dict[str, Dict] = {}
        self._by_path: Dict[str, Dict] = {}
        self._by_pick_code: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def add(self, item: Dict):
        """添加文件到索引"""
        with self._lock:
            fid = get_item_attr(item, "fid", "file_id")
            if fid:
                self._by_id[fid] = item

            path = item.get("_relative_path")
            if path:
                self._by_path[path] = item

            pick_code = get_item_attr(item, "pc", "pick_code")
            if pick_code:
                self._by_pick_code[pick_code] = item

    def get_by_id(self, file_id: str) -> Optional[Dict]:
        """通过 ID 查找"""
        with self._lock:
            return self._by_id.get(file_id)

    def get_by_path(self, path: str) -> Optional[Dict]:
        """通过路径查找"""
        with self._lock:
            return self._by_path.get(path.strip("/"))

    def get_by_pick_code(self, pick_code: str) -> Optional[Dict]:
        """通过 pick_code 查找"""
        with self._lock:
            return self._by_pick_code.get(pick_code)

    def clear(self):
        """清空索引"""
        with self._lock:
            self._by_id.clear()
            self._by_path.clear()
            self._by_pick_code.clear()

    def __len__(self):
        with self._lock:
            return len(self._by_id)
