"""
多网盘 STRM 网关系统

支持多种云存储提供商的统一 STRM 文件生成和流媒体网关
"""

# 导出核心接口和数据模型
from .core import (
    # 数据模型
    FileType,
    EventType,
    FileItem,
    FileEvent,
    AuthToken,
    QRCodeAuth,
    DriveInfo,
    DownloadInfo,
    # 异常
    CloudStorageError,
    AuthenticationError,
    TokenExpiredError,
    InvalidTokenError,
    FileNotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    NetworkError,
    ProviderNotSupportedError,
    # 接口
    AuthProvider,
    TokenWatcher,
    CloudStorageProvider,
)

# 导出 Provider 工厂和基类
from .providers import (
    ProviderFactory,
    provider_factory,
    BaseProvider,
)

# 导出配置
from .config import AppConfig, GatewayConfig, DatabaseConfig

# 导出服务
from .services.drive_service import DriveService, Drive
from .services.file_service import FileService
from .services.strm_service import StrmService

# 导出网关服务器
from .gateway.server import GatewayServer

# 自动导入所有 Provider（触发自动注册）
from .providers import drive_115  # noqa: F401

__all__ = [
    # 核心
    "FileType",
    "EventType",
    "FileItem",
    "FileEvent",
    "AuthToken",
    "QRCodeAuth",
    "DriveInfo",
    "DownloadInfo",
    "CloudStorageError",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidTokenError",
    "FileNotFoundError",
    "PermissionDeniedError",
    "RateLimitExceededError",
    "NetworkError",
    "ProviderNotSupportedError",
    "AuthProvider",
    "TokenWatcher",
    "CloudStorageProvider",
    # Providers
    "ProviderFactory",
    "provider_factory",
    "BaseProvider",
    # 配置
    "AppConfig",
    "GatewayConfig",
    "DatabaseConfig",
    # 服务
    "DriveService",
    "Drive",
    "FileService",
    "StrmService",
    # 网关
    "GatewayServer",
]

__version__ = "2.0.0"
