"""
Provider 基类

提供通用的 Provider 实现辅助
"""

from typing import List, Optional
from ..core.provider import CloudStorageProvider
from ..core.models import FileItem, FileType


class BaseProvider(CloudStorageProvider):
    """Provider 基类

    提供一些通用的辅助方法
    """

    def traverse_folder(
        self,
        folder_id: str,
        max_depth: Optional[int] = None,
        include_folders: bool = True
    ) -> List[FileItem]:
        """递归遍历文件夹

        Args:
            folder_id: 起始文件夹 ID
            max_depth: 最大深度（None 表示不限制）
            include_folders: 是否包含文件夹

        Returns:
            List[FileItem]: 所有文件列表
        """
        results = []
        queue = [(folder_id, 0)]  # (folder_id, depth)

        while queue:
            current_id, depth = queue.pop(0)

            # 检查深度限制
            if max_depth is not None and depth >= max_depth:
                continue

            # 获取当前文件夹内容
            items, _ = self.list_files(current_id)

            for item in items:
                if item.is_folder:
                    if include_folders:
                        results.append(item)
                    # 加入队列继续遍历
                    queue.append((item.id, depth + 1))
                else:
                    results.append(item)

        return results

    def filter_by_type(
        self,
        items: List[FileItem],
        file_types: List[FileType]
    ) -> List[FileItem]:
        """按文件类型过滤

        Args:
            items: 文件列表
            file_types: 要保留的文件类型

        Returns:
            List[FileItem]: 过滤后的列表
        """
        return [item for item in items if item.type in file_types]

    def filter_by_extension(
        self,
        items: List[FileItem],
        extensions: List[str]
    ) -> List[FileItem]:
        """按文件扩展名过滤

        Args:
            items: 文件列表
            extensions: 扩展名列表（如 [".mp4", ".mkv"]）

        Returns:
            List[FileItem]: 过滤后的列表
        """
        # 转换为小写便于比较
        extensions = [ext.lower() for ext in extensions]

        def has_extension(item: FileItem) -> bool:
            if item.is_folder:
                return False
            name_lower = item.name.lower()
            return any(name_lower.endswith(ext) for ext in extensions)

        return [item for item in items if has_extension(item)]
