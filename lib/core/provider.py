"""
云存储 Provider 接口

定义统一的云存储操作抽象
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from ..core.models import (
    FileItem, FileEvent, DriveInfo, DownloadInfo, AuthToken
)
from ..core.auth import AuthProvider


class CloudStorageProvider(ABC):
    """云存储提供者接口

    定义统一的云存储操作接口，支持不同网盘的适配
    """

    def __init__(self, auth_provider: AuthProvider, token_file: str):
        """
        Args:
            auth_provider: 认证提供者
            token_file: 令牌文件路径
        """
        self.auth_provider = auth_provider
        self.token_file = token_file
        self._token: Optional[AuthToken] = None

    @property
    def provider_type(self) -> str:
        """Provider 类型标识

        Returns:
            str: 类型（如 "115", "aliyun", "baidu"）
        """
        raise NotImplementedError

    @abstractmethod
    def authenticate(self) -> AuthToken:
        """执行认证流程

        Returns:
            AuthToken: 认证令牌

        Raises:
            AuthenticationError: 认证失败
        """
        pass

    @abstractmethod
    def get_drive_info(self) -> DriveInfo:
        """获取网盘信息

        Returns:
            DriveInfo: 网盘信息（用户 ID、空间等）

        Raises:
            CloudStorageError: 获取失败
        """
        pass

    # ==================== 文件操作 ====================

    @abstractmethod
    def list_files(
        self,
        folder_id: str,
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[List[FileItem], int]:
        """列出文件夹内容

        Args:
            folder_id: 文件夹 ID（根目录通常为 "0" 或 "root"）
            limit: 每页数量
            offset: 偏移量

        Returns:
            Tuple[List[FileItem], int]: (文件列表, 总数)

        Raises:
            FileNotFoundError: 文件夹不存在
            PermissionDeniedError: 无权限访问
        """
        pass

    @abstractmethod
    def get_file_info(self, file_id: str) -> FileItem:
        """获取文件详情

        Args:
            file_id: 文件 ID

        Returns:
            FileItem: 文件信息

        Raises:
            FileNotFoundError: 文件不存在
        """
        pass

    @abstractmethod
    def search_files(
        self,
        keyword: str,
        folder_id: Optional[str] = None,
        limit: int = 100
    ) -> List[FileItem]:
        """搜索文件

        Args:
            keyword: 搜索关键词
            folder_id: 限定搜索范围（可选）
            limit: 结果数量

        Returns:
            List[FileItem]: 匹配的文件列表
        """
        pass

    @abstractmethod
    def get_download_url(self, file_id: str, **kwargs) -> DownloadInfo:
        """获取文件下载链接

        Args:
            file_id: 文件 ID
            **kwargs: 额外参数（如过期时间等）

        Returns:
            DownloadInfo: 下载信息（URL、过期时间等）

        Raises:
            FileNotFoundError: 文件不存在
            PermissionDeniedError: 无下载权限
        """
        pass

    # ==================== 文件管理 ====================

    def create_folder(self, parent_id: str, name: str) -> FileItem:
        """创建文件夹

        Args:
            parent_id: 父文件夹 ID
            name: 文件夹名称

        Returns:
            FileItem: 新建的文件夹信息

        Raises:
            CloudStorageError: 创建失败
        """
        raise NotImplementedError("This provider does not support folder creation")

    def rename(self, file_id: str, new_name: str) -> FileItem:
        """重命名文件/文件夹

        Args:
            file_id: 文件 ID
            new_name: 新名称

        Returns:
            FileItem: 更新后的文件信息

        Raises:
            FileNotFoundError: 文件不存在
            CloudStorageError: 重命名失败
        """
        raise NotImplementedError("This provider does not support renaming")

    def move(self, file_id: str, target_folder_id: str) -> FileItem:
        """移动文件/文件夹

        Args:
            file_id: 文件 ID
            target_folder_id: 目标文件夹 ID

        Returns:
            FileItem: 更新后的文件信息

        Raises:
            FileNotFoundError: 文件不存在
            CloudStorageError: 移动失败
        """
        raise NotImplementedError("This provider does not support moving")

    def delete(self, file_id: str) -> bool:
        """删除文件/文件夹

        Args:
            file_id: 文件 ID

        Returns:
            bool: 是否成功

        Raises:
            FileNotFoundError: 文件不存在
            CloudStorageError: 删除失败
        """
        raise NotImplementedError("This provider does not support deletion")

    # ==================== 事件监听（可选） ====================

    def supports_events(self) -> bool:
        """是否支持事件监听

        Returns:
            bool: 是否支持
        """
        return False

    def get_events(
        self,
        from_event_id: Optional[str] = None,
        limit: int = 100
    ) -> List[FileEvent]:
        """获取文件变更事件

        Args:
            from_event_id: 起始事件 ID（获取之后的事件）
            limit: 最大数量

        Returns:
            List[FileEvent]: 事件列表

        Raises:
            NotImplementedError: Provider 不支持事件监听
        """
        raise NotImplementedError("This provider does not support event monitoring")

    # ==================== 辅助方法 ====================

    def ensure_authenticated(self) -> AuthToken:
        """确保已认证（自动刷新令牌）

        Returns:
            AuthToken: 有效令牌

        Raises:
            AuthenticationError: 认证失败
        """
        if self._token is None or self._token.is_expired():
            self._token = self.auth_provider.auto_refresh_token(self.token_file)
        return self._token

    def invalidate_token(self):
        """使令牌失效（强制下次重新认证）"""
        self._token = None
