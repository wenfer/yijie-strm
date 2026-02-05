"""
p115client 封装的 115 网盘 Provider

基于 p115client 库实现 115 网盘的文件操作
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, AsyncGenerator
from dataclasses import dataclass

from p115client import P115Client
from p115client.exception import P115OSError, P115LoginError

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """文件信息数据类"""
    id: str
    name: str
    is_dir: bool
    size: int = 0
    parent_id: str = "0"
    pick_code: Optional[str] = None
    sha1: Optional[str] = None
    path: str = ""
    time: int = 0


class P115Provider:
    """
    115 网盘 Provider
    
    基于 p115client 封装 115 网盘操作
    """

    # 视频文件扩展名
    VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.m2ts', '.rmvb'
    }

    # 音频文件扩展名
    AUDIO_EXTENSIONS = {
        '.mp3', '.flac', '.wav', '.aac', '.m4a', '.wma', '.ogg',
        '.ape', '.opus', '.alac', '.aiff'
    }

    def __init__(self, cookie_file: str):
        """
        初始化 Provider
        
        Args:
            cookie_file: Cookie 文件路径
        """
        self.cookie_file = Path(cookie_file).expanduser()
        self._client: Optional[P115Client] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> P115Client:
        """获取或创建客户端"""
        if self._client is None:
            # p115client 会自动处理 cookie 加载和刷新
            # 注意：必须传递 Path 对象而不是字符串
            # check_for_relogin=True 会在认证失效时自动刷新 cookie
            self._client = P115Client(self.cookie_file, check_for_relogin=True)
        return self._client

    async def close(self):
        """关闭客户端"""
        if self._client:
            # p115client 不需要显式关闭
            self._client = None

    async def is_authenticated(self) -> bool:
        """检查是否已认证"""
        try:
            client = await self._get_client()
            # 尝试获取根目录文件列表来验证认证状态
            resp = await client.fs_files(0, async_=True)
            return resp.get("state", False)
        except Exception as e:
            logger.warning(f"Authentication check failed: {e}")
            return False

    async def list_files(
            self,
            cid: str = "0",
            limit: int = 100,
            offset: int = 0,
            **kwargs
    ) -> Tuple[List[FileInfo], int]:
        """
        获取目录下的文件列表
        
        Args:
            cid: 文件夹 ID
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            (文件列表, 总数)
        """
        client = await self._get_client()

        try:
            resp = await client.fs_files(
                cid,
                limit=limit,
                offset=offset,
                async_=True,
                **kwargs
            )

            if not resp.get("state", False):
                error_msg = resp.get("error", "Unknown error")
                logger.error(f"Failed to list files: {error_msg}")
                return [], 0

            # p115client 返回的数据结构：resp["data"] 是文件列表
            # count 等字段直接在 resp 中
            files = resp.get("data", [])
            total = resp.get("count", 0)

            items = []
            for item in files:
                file_info = self._parse_file_item(item, cid)
                items.append(file_info)

            return items, total

        except Exception as e:
            logger.exception(f"Error listing files: {e}")
            return [], 0

    async def list_all_files(
            self,
            cid: str = "0",
            **kwargs
    ) -> List[FileInfo]:
        """
        获取目录下的所有文件（自动分页）
        
        Args:
            cid: 文件夹 ID
            
        Returns:
            文件列表
        """
        all_items = []
        offset = 0
        limit = 1000  # p115client 支持较大的分页

        while True:
            items, total = await self.list_files(cid, limit=limit, offset=offset, **kwargs)
            all_items.extend(items)

            if len(all_items) >= total:
                break

            offset += limit

        return all_items

    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """
        获取文件/文件夹详细信息
        
        Args:
            file_id: 文件 ID
            
        Returns:
            文件信息
        """
        client = await self._get_client()

        try:
            resp = await client.fs_file(file_id, async_=True)

            if not resp.get("state", False):
                return None

            data = resp.get("data", [])
            if not data:
                return None

            return self._parse_file_item(data[0])

        except Exception as e:
            logger.exception(f"Error getting file info: {e}")
            return None

    async def search_files(
            self,
            keyword: str,
            cid: str = "0",
            limit: int = 100,
            **kwargs
    ) -> List[FileInfo]:
        """
        搜索文件
        
        Args:
            keyword: 搜索关键词
            cid: 搜索目录
            limit: 最大结果数
            
        Returns:
            文件列表
        """
        client = await self._get_client()

        try:
            resp = await client.fs_search(
                {
                    "search_value": keyword,
                    "cid": cid,
                    "limit": limit,
                    **kwargs
                },
                async_=True
            )

            if not resp.get("state", False):
                return []

            data = resp.get("data", [])
            return [self._parse_file_item(item) for item in data]

        except Exception as e:
            logger.exception(f"Error searching files: {e}")
            return []

    async def get_download_url(
            self,
            pick_code: str,
            id: int,
            user_agent: Optional[str] = None
    ) -> Optional[str]:
        """
        获取文件下载链接
        
        Args:
            pick_code: 文件的 pick_code
            id: 文件id
            user_agent: 可选的 User-Agent
            
        Returns:
            下载链接
        """
        client = await self._get_client()
        if id > 0 and not pick_code:
            logger.warning(f"Invalid id: {id}")
            pick_code = client.to_pickcode(id)
        if not pick_code:
            return None
        try:
            headers = {"user-agent": user_agent} if user_agent else None
            url = await client.download_url(
                pick_code,
                headers=headers,
                app="chrome",
                async_=True
            )
            return url

        except P115LoginError as e:
            logger.warning(f"Cookie expired for pick_code {pick_code}: {e}")
            # 重置客户端，触发 cookie 重新加载
            self._client = None
            # 重试一次
            try:
                client = await self._get_client()
                headers = {"user-agent": user_agent} if user_agent else None
                url = await client.download_url(
                    pick_code,
                    headers=headers,
                    app="android",
                    async_=True
                )
                logger.info(f"Retry successful after cookie refresh for pick_code: {pick_code}")
                return url
            except Exception as retry_error:
                logger.error(f"Retry failed after cookie refresh: {retry_error}")
                return None
        except (FileNotFoundError, IsADirectoryError):
            logger.warning(f"File not found for pick_code: {pick_code}")
            return None
        except Exception as e:
            logger.exception(f"Error getting download URL: {e}")
            return None

    async def to_pickcode(self, file_id: str) -> Optional[str]:
        """
        将文件 ID 转换为 pick_code
        
        Args:
            file_id: 文件 ID
            
        Returns:
            pick_code
        """
        client = await self._get_client()

        try:
            return client.to_pickcode(int(file_id))
        except Exception as e:
            logger.exception(f"Error converting to pickcode: {e}")
            return None

    async def to_id(self, pick_code: str) -> int:
        """
        将 pick_code 转换为文件 ID
        
        Args:
            pick_code: pick_code
            
        Returns:
            文件 ID
        """
        client = await self._get_client()

        try:
            return client.to_id(pick_code)
        except Exception as e:
            logger.exception(f"Error converting to id: {e}")
            return 0

    async def iterdir(
            self,
            cid: str = "0",
            **kwargs
    ) -> AsyncGenerator[FileInfo, None]:
        """
        异步迭代目录内容
        
        Args:
            cid: 文件夹 ID
            
        Yields:
            FileInfo 对象
        """
        client = await self._get_client()

        try:
            async for item in client.iterdir(cid, async_=True, **kwargs):
                yield self._parse_file_item(item, cid)
        except Exception as e:
            logger.exception(f"Error iterating directory: {e}")

    async def iter_files(
            self,
            cid: str = "0",
            recursive: bool = True,
            **kwargs
    ) -> AsyncGenerator[FileInfo, None]:
        """
        异步迭代文件（递归遍历）
        
        Args:
            cid: 起始文件夹 ID
            recursive: 是否递归
            
        Yields:
            FileInfo 对象
        """
        if not recursive:
            async for item in self.iterdir(cid, **kwargs):
                if not item.is_dir:
                    yield item
            return

        # 递归遍历
        stack = [cid]
        while stack:
            current_cid = stack.pop()

            async for item in self.iterdir(current_cid, **kwargs):
                if item.is_dir:
                    stack.append(item.id)
                else:
                    yield item

    def _parse_file_item(self, item: Dict[str, Any], parent_id: str = "0") -> FileInfo:
        """
        解析 p115client 返回的文件数据

        Args:
            item: p115client 返回的文件数据
            parent_id: 父目录 ID

        Returns:
            FileInfo 对象
        """
        # p115client fs_files 返回的字段格式
        # cid = 文件ID, n = 文件名, s = 文件大小, pc = pick_code
        # pid = 父目录ID, fc = 文件类别(0=文件, 1=文件夹)
        file_id = str(item.get("cid", "0"))
        name = item.get("n", "")
        size = item.get("s", 0)

        # 判断是否为文件夹
        # 根据 115 API 文档：fc (file_category) 0=文件夹, 1=视频, 2=音频, 3=图片, 4=文档, 5=其他
        fc = item.get("fc")
        if fc is not None:
            is_dir = int(fc) == 0
        else:
            # 兜底：根据 sha 字段判断（文件有sha，文件夹sha为空）
            sha = item.get("sha", "")
            is_dir = sha == "" or sha is None

        pick_code = item.get("pc", "")
        sha1 = item.get("sha", "")

        # 获取父目录 ID
        pid = item.get("pid", parent_id)

        # 获取修改时间
        time_str = item.get("t", "0")
        try:
            timestamp = int(time_str)
        except (ValueError, TypeError):
            timestamp = 0

        return FileInfo(
            id=file_id,
            name=name,
            is_dir=is_dir,
            size=int(size) if size else 0,
            parent_id=str(pid),
            pick_code=pick_code,
            sha1=sha1,
            time=timestamp,
        )

    def is_video_file(self, filename: str) -> bool:
        """判断是否为视频文件"""
        ext = Path(filename).suffix.lower()
        return ext in self.VIDEO_EXTENSIONS

    def is_audio_file(self, filename: str) -> bool:
        """判断是否为音频文件"""
        ext = Path(filename).suffix.lower()
        return ext in self.AUDIO_EXTENSIONS

    def is_media_file(self, filename: str) -> bool:
        """判断是否为媒体文件"""
        return self.is_video_file(filename) or self.is_audio_file(filename)

    async def download_file(
            self,
            pick_code: str,
            file_id: int,
            output_path: Path,
            user_agent: Optional[str] = None
    ) -> bool:
        """
        下载文件到本地

        Args:
            pick_code: 文件的 pick_code
            file_id: 文件 ID
            output_path: 输出文件路径
            user_agent: 可选的 User-Agent

        Returns:
            是否下载成功
        """
        import httpx

        try:
            # 获取下载链接
            download_url = await self.get_download_url(pick_code, file_id, user_agent)
            if not download_url:
                logger.warning(f"Failed to get download URL for pick_code: {pick_code}")
                return False

            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 设置请求头
            headers = {
                "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            # 流式下载文件
            async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
                async with client.stream("GET", download_url, headers=headers) as response:
                    if response.status_code != 200:
                        logger.error(f"Download failed with status {response.status_code} for {pick_code}")
                        return False

                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)

            logger.info(f"Downloaded file to: {output_path}")
            return True

        except Exception as e:
            logger.exception(f"Error downloading file {pick_code}: {e}")
            # 如果下载失败，删除可能创建的不完整文件
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            return False


# Provider 管理器
class ProviderManager:
    """Provider 管理器"""

    def __init__(self):
        self._providers: Dict[str, P115Provider] = {}

    async def get_provider(self, drive_id: str, cookie_file: str) -> P115Provider:
        """
        获取或创建 Provider
        
        Args:
            drive_id: 网盘 ID
            cookie_file: Cookie 文件路径
            
        Returns:
            P115Provider 实例
        """
        if drive_id not in self._providers:
            self._providers[drive_id] = P115Provider(cookie_file)
        return self._providers[drive_id]

    async def remove_provider(self, drive_id: str):
        """移除 Provider"""
        if drive_id in self._providers:
            await self._providers[drive_id].close()
            del self._providers[drive_id]

    async def close_all(self):
        """关闭所有 Provider"""
        for provider in self._providers.values():
            await provider.close()
        self._providers.clear()


# 全局 Provider 管理器
provider_manager = ProviderManager()
