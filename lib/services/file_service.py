"""
文件服务模块

提供文件遍历、路径解析、下载链接缓存等高级功能
支持任意 CloudStorageProvider 实现
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

from lib.core.provider import CloudStorageProvider
from lib.core.models import FileItem, FileType

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
    """文件服务 - 提供高级文件操作功能（通过 Provider 接口）"""

    def __init__(self, provider: CloudStorageProvider, cache_ttl: int = 3600):
        """
        Args:
            provider: 云存储 Provider
            cache_ttl: 下载链接缓存时间（秒）
        """
        self.provider = provider
        self._url_cache = DownloadUrlCache(ttl=cache_ttl)

    # ==================== 下载链接服务 ====================

    def get_download_url(self, file_item: FileItem, use_cache: bool = True) -> Optional[str]:
        """获取下载链接（支持缓存）

        Args:
            file_item: 文件项
            use_cache: 是否使用缓存

        Returns:
            下载 URL，失败返回 None
        """
        # 使用 download_id（如 115 的 pick_code）作为缓存键
        cache_key = file_item.download_id or file_item.id

        if use_cache:
            cached = self._url_cache.get(cache_key)
            if cached:
                logger.debug(f"file_service.py:104 - Cache hit for file: {file_item.name}")
                return cached

        try:
            # 使用 download_id（如 pick_code）获取下载链接
            download_id = file_item.download_id or file_item.id
            download_info = self.provider.get_download_url(download_id)

            if download_info and download_info.url and use_cache:
                self._url_cache.set(cache_key, download_info.url)

            return download_info.url if download_info else None

        except Exception as e:
            logger.error(f"file_service.py:119 - Failed to get download URL for {file_item.name}: {e}")
            return None

    # ==================== 文件遍历服务 ====================

    def traverse_folder(
        self,
        root_folder_id: str,
        root_name: str = "",
        item_handler: Callable[[FileItem, str], None] = None,
        folder_handler: Callable[[FileItem, str], None] = None,
        max_depth: int = -1
    ) -> List[FileItem]:
        """
        BFS 遍历文件夹

        Args:
            root_folder_id: 根目录 ID
            root_name: 根目录名称
            item_handler: 文件处理回调 (item, relative_path)
            folder_handler: 文件夹处理回调 (item, relative_path)
            max_depth: 最大遍历深度，-1 表示无限制

        Returns:
            所有遍历到的项目列表
        """
        all_items = []
        all_items_lock = threading.Lock()
        visited = set()
        visited_lock = threading.Lock()

        # 任务队列: (folder_id, name, parent_path, depth)
        task_queue = deque()
        task_queue.append((root_folder_id, root_name, "", 0))

        with visited_lock:
            visited.add(root_folder_id)

        def _process_directory(folder_id: str, name: str, parent_path: str, depth: int):
            """处理单个目录"""
            try:
                items, _ = self.provider.list_files(folder_id, limit=10000)
                if not items:
                    return [], []

                current_path = os.path.join(parent_path, name).replace("\\", "/") if parent_path else name
                processed_items = []
                subdirs = []

                for item in items:
                    rel_path = os.path.join(current_path, item.name).replace("\\", "/")
                    processed_items.append((item, rel_path, depth))

                    if item.is_folder:
                        subdirs.append((item.id, item.name))

                return processed_items, subdirs

            except Exception as e:
                logger.error(f"file_service.py:186 - Error processing directory {folder_id}: {e}")
                return [], []

        # 单线程遍历（避免并发问题）
        while task_queue:
            folder_id, name, parent_path, depth = task_queue.popleft()

            if max_depth >= 0 and depth > max_depth:
                continue

            items, subdirs = _process_directory(folder_id, name, parent_path, depth)

            # 收集结果
            for item, rel_path, item_depth in items:
                with all_items_lock:
                    all_items.append(item)

                if item.is_folder:
                    if folder_handler:
                        folder_handler(item, rel_path)
                else:
                    if item_handler:
                        item_handler(item, rel_path)

            # 添加子目录任务
            if max_depth < 0 or depth < max_depth:
                for sub_id, sub_name in subdirs:
                    with visited_lock:
                        if sub_id not in visited:
                            visited.add(sub_id)
                            new_path = os.path.join(parent_path, name).replace("\\", "/") if parent_path else name
                            task_queue.append((sub_id, sub_name, new_path, depth + 1))

        return all_items

    # ==================== 路径解析服务 ====================

    def resolve_path(self, path: str, start_folder_id: str = '0') -> Optional[FileItem]:
        """
        解析路径到文件/文件夹项

        Args:
            path: 路径字符串，如 "/电影/科幻/xxx.mkv"
            start_folder_id: 起始目录 ID

        Returns:
            找到的文件/文件夹项，未找到返回 None
        """
        path = path.strip("/")
        if not path:
            # 返回根目录（构造一个虚拟 FileItem）
            return FileItem(
                id=start_folder_id,
                name="Root",
                type=FileType.FOLDER,
                size=0,
                parent_id=""
            )

        parts = path.split("/")
        current_folder_id = start_folder_id

        for i, part in enumerate(parts):
            try:
                items, _ = self.provider.list_files(current_folder_id, limit=10000)
                found = None

                for item in items:
                    if item.name == part:
                        found = item
                        break

                if not found:
                    logger.warning(f"file_service.py:270 - Path component not found: {part}")
                    return None

                if i < len(parts) - 1:
                    # 中间路径必须是文件夹
                    if not found.is_folder:
                        logger.warning(f"file_service.py:276 - Path component is not a folder: {part}")
                        return None
                    current_folder_id = found.id
                else:
                    return found

            except Exception as e:
                logger.error(f"file_service.py:283 - Error resolving path: {e}")
                return None

        return None

    # ==================== 文件统计服务 ====================

    def get_folder_stats(self, folder_id: str) -> Dict:
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

        def _count_item(item: FileItem, path: str):
            if item.is_folder:
                stats["total_folders"] += 1
            else:
                stats["total_files"] += 1
                stats["total_size"] += item.size

                # 统计文件类型
                ext = os.path.splitext(item.name)[1].lower()
                if ext:
                    stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1

        self.traverse_folder(folder_id, "", item_handler=_count_item, folder_handler=_count_item)
        return stats


class FileIndex:
    """文件索引 - 用于快速查找文件"""

    def __init__(self):
        self._by_id: Dict[str, FileItem] = {}
        self._by_path: Dict[str, FileItem] = {}
        self._by_download_id: Dict[str, FileItem] = {}
        self._lock = threading.Lock()

    def add(self, item: FileItem, relative_path: str = ""):
        """添加文件到索引"""
        with self._lock:
            self._by_id[item.id] = item

            if relative_path:
                self._by_path[relative_path] = item

            if item.download_id:
                self._by_download_id[item.download_id] = item

    def get_by_id(self, file_id: str) -> Optional[FileItem]:
        """通过 ID 查找"""
        with self._lock:
            return self._by_id.get(file_id)

    def get_by_path(self, path: str) -> Optional[FileItem]:
        """通过路径查找"""
        with self._lock:
            return self._by_path.get(path.strip("/"))

    def get_by_download_id(self, download_id: str) -> Optional[FileItem]:
        """通过 download_id 查找（如 115 的 pick_code）"""
        with self._lock:
            return self._by_download_id.get(download_id)

    def clear(self):
        """清空索引"""
        with self._lock:
            self._by_id.clear()
            self._by_path.clear()
            self._by_download_id.clear()

    def __len__(self):
        with self._lock:
            return len(self._by_id)
