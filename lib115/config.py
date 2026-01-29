"""
115 网盘 API 配置模块
支持 STRM 网关服务的配置管理
"""
from __future__ import annotations
import os
from typing import Dict, Union
from dataclasses import dataclass, field


@dataclass
class ApiConfig:
    """API 端点配置"""
    FILE_LIST_API_URL: str = "https://proapi.115.com/open/ufile/files"
    SEARCH_API_URL: str = "https://proapi.115.com/open/ufile/search"
    DOWNLOAD_API_URL: str = "https://proapi.115.com/open/ufile/downurl"
    GET_FOLDER_INFO_API_URL: str = "https://proapi.115.com/open/folder/get_info"
    MOVE_API_URL: str = "https://proapi.115.com/open/ufile/move"
    ADD_FOLDER_API_URL: str = "https://proapi.115.com/open/folder/add"
    UPDATE_FILE_API_URL: str = "https://proapi.115.com/open/ufile/update"
    DELETE_FILE_API_URL: str = "https://proapi.115.com/open/ufile/delete"
    CLOUD_DOWNLOAD_API_URL: str = "https://proapi.115.com/open/offline/add_task_urls"
    GET_UPLOAD_TOKEN_API_URL: str = "https://proapi.115.com/open/upload/get_token"
    UPLOAD_INIT_API_URL: str = "https://proapi.115.com/open/upload/init"
    UPLOAD_RESUME_API_URL: str = "https://proapi.115.com/open/upload/resume"


@dataclass
class AuthConfig:
    """认证相关配置"""
    AUTH_DEVICE_CODE_URL: str = "https://passportapi.115.com/open/authDeviceCode"
    QRCODE_STATUS_URL: str = "https://qrcodeapi.115.com/get/status/"
    DEVICE_CODE_TO_TOKEN_URL: str = "https://passportapi.115.com/open/deviceCodeToToken"
    REFRESH_TOKEN_URL: str = "https://passportapi.115.com/open/refreshToken"
    # Token 本地存储路径（默认在用户目录下）
    TOKEN_FILE_PATH: str = os.path.expanduser("~/.115_token.json")

    # Client ID 映射表
    CLIENT_ID_MAP: Dict[int, int] = field(default_factory=lambda: {
        1: 100195135,
        2: 100195145,
        3: 100195181,
        4: 100196251,  # Infuse
        5: 100195137,
        6: 100195161,
        7: 100197303,
        8: 100195313
    })

    def get_client_id(self, app: int = 4) -> int:
        """获取指定应用的 Client ID"""
        return self.CLIENT_ID_MAP.get(app, 100196251)


@dataclass
class NetworkConfig:
    """网络请求配置"""
    USER_AGENT: str = "Infuse/8.3.5433"
    REFERER_DOMAIN: str = "https://proapi.115.com/"
    DEFAULT_CONNECT_TIMEOUT: int = 300
    DEFAULT_READ_TIMEOUT: int = 300
    API_RPS_LIMIT: int = 2
    API_CONCURRENT_THREADS: int = 10


@dataclass
class GatewayConfig:
    """STRM 网关服务配置"""
    HOST: str = "0.0.0.0"
    PORT: int = 8115
    DEBUG: bool = False
    CACHE_TTL: int = 3600  # 下载链接缓存时间（秒）
    STRM_BASE_URL: str = ""  # STRM 文件中的基础 URL，留空则自动检测
    ENABLE_CORS: bool = True
    LOG_LEVEL: str = "INFO"


@dataclass
class AppConfig:
    """应用主配置"""
    api: ApiConfig = field(default_factory=ApiConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)

    # 文件操作配置
    API_FETCH_LIMIT: int = 1150
    MAX_SEARCH_EXPLORE_COUNT: int = 10000
    ROOT_CID: str = '0'

    # 上传配置
    CHUNK_SIZE: int = 24 * 1024 * 1024
    UPLOAD_RETRY_COUNT: int = 3
    UPLOAD_RETRY_DELAY_SECONDS: int = 5
    UPLOAD_CONCURRENT_THREADS: int = 4

    # 下载配置
    DOWNLOAD_CONCURRENT_THREADS: int = 10

    # 移动操作配置
    MOVE_MAX_FILE_IDS: int = 100000
    MOVE_RATE_LIMIT_FILES_PER_SECOND: int = 4000

    # 文件名处理
    ALLOWED_SPECIAL_FILENAME_CHARS: str = "._- ()[]{}+#@&"
    MAX_SAFE_FILENAME_LENGTH: int = 1150

    # 默认浏览参数
    COMMON_BROWSE_FETCH_PARAMS: Dict = field(default_factory=lambda: {
        "o": "file_name",
        "asc": "1",
        "show_dir": "1",
        "custom_order": "1"
    })

    # 预设文件夹
    PREDEFINED_FOLDERS: Dict[str, int] = field(default_factory=lambda: {
        '剧集': 3177795036869964618,
        '电影': 3177794855273378210,
        '纪录片': 3112736229787318869,
        '其他文件': 3112736324528257038,
        '综艺节目': 3112736070923860587,
    })

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """从环境变量加载配置"""
        config = cls()

        # Gateway 配置
        config.gateway.HOST = os.environ.get('GATEWAY_HOST', config.gateway.HOST)
        config.gateway.PORT = int(os.environ.get('GATEWAY_PORT', config.gateway.PORT))
        config.gateway.DEBUG = os.environ.get('GATEWAY_DEBUG', '').lower() == 'true'
        config.gateway.STRM_BASE_URL = os.environ.get('STRM_BASE_URL', '')
        config.gateway.CACHE_TTL = int(os.environ.get('CACHE_TTL', config.gateway.CACHE_TTL))

        # Auth 配置
        config.auth.TOKEN_FILE_PATH = os.environ.get(
            'TOKEN_FILE_PATH',
            config.auth.TOKEN_FILE_PATH
        )

        # Network 配置
        config.network.API_RPS_LIMIT = int(os.environ.get(
            'API_RPS_LIMIT',
            config.network.API_RPS_LIMIT
        ))

        return config


# 全局默认配置实例
default_config = AppConfig()
