"""
核心抽象层

导出核心接口和数据模型
"""

from .models import (
    FileType,
    EventType,
    FileItem,
    FileEvent,
    AuthToken,
    QRCodeAuth,
    DriveInfo,
    DownloadInfo,
)

from .exceptions import (
    CloudStorageError,
    AuthenticationError,
    TokenExpiredError,
    InvalidTokenError,
    FileNotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    NetworkError,
    ProviderNotSupportedError,
)

from .auth import AuthProvider, TokenWatcher
from .provider import CloudStorageProvider

__all__ = [
    # 模型
    "FileType",
    "EventType",
    "FileItem",
    "FileEvent",
    "AuthToken",
    "QRCodeAuth",
    "DriveInfo",
    "DownloadInfo",
    # 异常
    "CloudStorageError",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "FileNotFoundError",
    "PermissionDeniedError",
    "RateLimitExceededError",
    "NetworkError",
    "ProviderNotSupportedError",
    # 接口
    "AuthProvider",
    "TokenWatcher",
    "CloudStorageProvider",
]
