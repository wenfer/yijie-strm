"""
115 网盘特定配置
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Config115:
    """115 网盘配置"""

    # API 端点
    FILE_LIST_API_URL: str = "https://proapi.115.com/open/ufile/files"
    SEARCH_API_URL: str = "https://proapi.115.com/open/ufile/search"
    DOWNLOAD_API_URL: str = "https://proapi.115.com/open/ufile/downurl"
    GET_FOLDER_INFO_API_URL: str = "https://proapi.115.com/open/folder/get_info"
    MOVE_API_URL: str = "https://proapi.115.com/open/ufile/move"
    ADD_FOLDER_API_URL: str = "https://proapi.115.com/open/folder/add"
    UPDATE_FILE_API_URL: str = "https://proapi.115.com/open/ufile/update"
    DELETE_FILE_API_URL: str = "https://proapi.115.com/open/ufile/delete"
    LIFE_BEHAVIOR_API_URL: str = "https://proapi.115.com/android/2.0/life/behavior_detail"

    # 认证端点
    AUTH_DEVICE_CODE_URL: str = "https://passportapi.115.com/open/authDeviceCode"
    QRCODE_STATUS_URL: str = "https://qrcodeapi.115.com/get/status/"
    DEVICE_CODE_TO_TOKEN_URL: str = "https://passportapi.115.com/open/deviceCodeToToken"
    REFRESH_TOKEN_URL: str = "https://passportapi.115.com/open/refreshToken"

    # Client ID 映射表
    CLIENT_ID_MAP: Dict[int, int] = field(default_factory=lambda: {
        1: 100195135,
        2: 100195145,
        3: 100195181,
        4: 100196251,  # Infuse（默认）
        5: 100195137,
        6: 100195161,
        7: 100197303,
        8: 100195313
    })

    # 网络配置
    USER_AGENT: str = "Infuse/8.3.5433"
    REFERER_DOMAIN: str = "https://proapi.115.com/"
    DEFAULT_CONNECT_TIMEOUT: int = 300
    DEFAULT_READ_TIMEOUT: int = 300
    API_RPS_LIMIT: int = 2
    API_CONCURRENT_THREADS: int = 10

    # 默认浏览参数
    COMMON_BROWSE_PARAMS: Dict = field(default_factory=lambda: {
        "o": "file_name",
        "asc": "1",
        "show_dir": "1",
        "custom_order": "1"
    })

    # 分页配置
    API_FETCH_LIMIT: int = 1150

    def get_client_id(self, app: int = 4) -> int:
        """获取指定应用的 Client ID"""
        return self.CLIENT_ID_MAP.get(app, 100196251)


# 默认配置实例
default_config = Config115()
