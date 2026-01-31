"""
115 网盘 Provider 实现

实现 CloudStorageProvider 接口
"""
import logging
from typing import List, Tuple, Optional

from ...core.provider import CloudStorageProvider
from ...core.models import (
    FileItem, FileEvent, DriveInfo, DownloadInfo, AuthToken
)
from ...core.exceptions import (
    CloudStorageError, FileNotFoundError, PermissionDeniedError
)
from ..base import BaseProvider
from .auth import Auth115
from .client import Client115
from .models import convert_to_file_item, convert_to_file_items, convert_to_file_event
from .config import Config115, default_config

logger = logging.getLogger(__name__)


class Provider115(BaseProvider):
    """115 网盘 Provider

    实现云存储统一接口
    """

    def __init__(self, token_file: str, config: Config115 = None):
        """
        Args:
            token_file: Token 文件路径
            config: 115 配置（可选）
        """
        self.config = config or default_config
        auth_provider = Auth115(self.config)
        super().__init__(auth_provider, token_file)

        self.client = Client115(self.config)

    @property
    def provider_type(self) -> str:
        return "115"

    def authenticate(self) -> AuthToken:
        """执行认证流程"""
        return self.auth_provider.auto_refresh_token(self.token_file)

    def get_drive_info(self) -> DriveInfo:
        """获取网盘信息

        注意：115 API 没有提供用户信息接口，这里返回基本信息
        """
        token = self.ensure_authenticated()

        # 从 token 中提取用户 ID
        user_id = token.raw_data.get("user_id", "") if token.raw_data else ""

        return DriveInfo(
            drive_id=f"115_{user_id}" if user_id else "115_unknown",
            drive_type="115",
            name="115 网盘",
            user_id=user_id,
            space_total=None,  # 115 API 不提供
            space_used=None,
            raw_data=token.raw_data
        )

    # ==================== 文件操作 ====================

    def list_files(
        self,
        folder_id: str,
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[List[FileItem], int]:
        """列出文件夹内容"""
        token = self.ensure_authenticated()

        try:
            items_115, total = self.client.list_files(
                token.access_token,
                cid=folder_id,
                limit=limit,
                offset=offset
            )

            items = convert_to_file_items(items_115)
            return items, total

        except Exception as e:
            logger.error(f"provider.py:96 - Failed to list files in folder {folder_id}: {e}")
            raise CloudStorageError(f"Failed to list files: {e}")

    def get_file_info(self, file_id: str) -> FileItem:
        """获取文件详情"""
        token = self.ensure_authenticated()

        try:
            item_115 = self.client.get_item_info(token.access_token, file_id)
            if not item_115:
                raise FileNotFoundError(f"File {file_id} not found")

            return convert_to_file_item(item_115)

        except Exception as e:
            logger.error(f"provider.py:113 - Failed to get file info for {file_id}: {e}")
            if isinstance(e, FileNotFoundError):
                raise
            raise CloudStorageError(f"Failed to get file info: {e}")

    def search_files(
        self,
        keyword: str,
        folder_id: Optional[str] = None,
        limit: int = 100
    ) -> List[FileItem]:
        """搜索文件"""
        token = self.ensure_authenticated()

        try:
            items_115, _ = self.client.search(
                token.access_token,
                keyword=keyword,
                cid=folder_id or '0',
                limit=limit
            )

            return convert_to_file_items(items_115)

        except Exception as e:
            logger.error(f"provider.py:138 - Failed to search files: {e}")
            raise CloudStorageError(f"Failed to search: {e}")

    def get_download_url(self, file_id: str, **kwargs) -> DownloadInfo:
        """获取文件下载链接

        Args:
            file_id: 对于 115，这是 pick_code（从 FileItem.download_id 获取）
        """
        token = self.ensure_authenticated()

        try:
            url = self.client.get_download_url(token.access_token, file_id)
            if not url:
                raise FileNotFoundError(f"Download URL not found for pick_code: {file_id}")

            return DownloadInfo(
                url=url,
                expires_at=None,  # 115 不提供过期时间，需要缓存管理
                headers=None
            )

        except Exception as e:
            logger.error(f"provider.py:163 - Failed to get download URL for {file_id}: {e}")
            if isinstance(e, FileNotFoundError):
                raise
            raise CloudStorageError(f"Failed to get download URL: {e}")

    # ==================== 文件管理 ====================

    def create_folder(self, parent_id: str, name: str) -> FileItem:
        """创建文件夹"""
        token = self.ensure_authenticated()

        try:
            folder_id, folder_name, error = self.client.create_folder(
                token.access_token,
                parent_id,
                name
            )

            if error:
                raise CloudStorageError(f"Failed to create folder: {error}")

            # 115 API 只返回 folder_id 和 folder_name，需要构造 FileItem
            from ...core.models import FileType
            return FileItem(
                id=folder_id,
                name=folder_name,
                type=FileType.FOLDER,
                size=0,
                parent_id=parent_id
            )

        except Exception as e:
            logger.error(f"provider.py:197 - Failed to create folder: {e}")
            if isinstance(e, CloudStorageError):
                raise
            raise CloudStorageError(f"Failed to create folder: {e}")

    def rename(self, file_id: str, new_name: str) -> FileItem:
        """重命名文件/文件夹"""
        token = self.ensure_authenticated()

        try:
            success, updated_name, error = self.client.rename(
                token.access_token,
                file_id,
                new_name
            )

            if not success:
                raise CloudStorageError(f"Failed to rename: {error}")

            # 获取更新后的文件信息
            return self.get_file_info(file_id)

        except Exception as e:
            logger.error(f"provider.py:222 - Failed to rename file {file_id}: {e}")
            if isinstance(e, CloudStorageError):
                raise
            raise CloudStorageError(f"Failed to rename: {e}")

    def move(self, file_id: str, target_folder_id: str) -> FileItem:
        """移动文件/文件夹"""
        token = self.ensure_authenticated()

        try:
            success = self.client.move(
                token.access_token,
                [file_id],
                target_folder_id
            )

            if not success:
                raise CloudStorageError("Failed to move file")

            # 获取更新后的文件信息
            return self.get_file_info(file_id)

        except Exception as e:
            logger.error(f"provider.py:246 - Failed to move file {file_id}: {e}")
            if isinstance(e, CloudStorageError):
                raise
            raise CloudStorageError(f"Failed to move: {e}")

    def delete(self, file_id: str) -> bool:
        """删除文件/文件夹"""
        token = self.ensure_authenticated()

        try:
            success, error = self.client.delete(
                token.access_token,
                [file_id]
            )

            if not success:
                raise CloudStorageError(f"Failed to delete: {error}")

            return True

        except Exception as e:
            logger.error(f"provider.py:268 - Failed to delete file {file_id}: {e}")
            if isinstance(e, CloudStorageError):
                raise
            raise CloudStorageError(f"Failed to delete: {e}")

    # ==================== 事件监听 ====================

    def supports_events(self) -> bool:
        """115 支持事件监听"""
        return True

    def get_events(
        self,
        from_event_id: Optional[str] = None,
        limit: int = 100
    ) -> List[FileEvent]:
        """获取文件变更事件

        Args:
            from_event_id: 起始事件 ID（暂不支持，返回最新事件）
            limit: 最大数量

        Returns:
            事件列表（按时间倒序）
        """
        token = self.ensure_authenticated()

        try:
            result = self.client.get_life_behavior_list(
                token.access_token,
                type="",  # 获取所有类型
                limit=limit
            )

            if not result or "list" not in result:
                return []

            events_115 = result["list"]

            # 转换为 FileEvent（过滤掉无法识别的事件）
            events = []
            for event_115 in events_115:
                event = convert_to_file_event(event_115)
                if event:
                    events.append(event)

            return events

        except Exception as e:
            logger.error(f"provider.py:318 - Failed to get events: {e}")
            raise CloudStorageError(f"Failed to get events: {e}")
