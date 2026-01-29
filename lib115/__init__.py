"""
lib115 - 115 网盘 Python SDK

支持 STRM 网关服务的模块化 115 网盘客户端库

模块结构:
- config: 配置管理
- auth: Token 认证管理
- api: 核心 API 客户端
- services: 高级服务（文件服务、STRM 服务）
- gateway: HTTP 网关服务
- utils: 辅助工具

快速开始:
    from lib115 import Client115, StrmService, GatewayServer

    # 使用 API 客户端
    with Client115() as client:
        items, total = client.list_files('0')
        for item in items:
            print(item['fn'])

    # 启动 STRM 网关
    server = GatewayServer()
    server.start()
"""

__version__ = "1.0.0"

# 核心导出
from .config import AppConfig, default_config
from .api import Client115, is_folder, get_item_attr
from .auth import TokenManager, TokenWatcher
from .services import FileService, StrmService, StrmGenerator
from .gateway import GatewayServer, run_gateway
from .utils import format_bytes, parse_size, safe_filename, is_video_file, is_media_file

__all__ = [
    # 版本
    '__version__',

    # 配置
    'AppConfig',
    'default_config',

    # API 客户端
    'Client115',
    'is_folder',
    'get_item_attr',

    # 认证
    'TokenManager',
    'TokenWatcher',

    # 服务
    'FileService',
    'StrmService',
    'StrmGenerator',

    # 网关
    'GatewayServer',
    'run_gateway',

    # 工具
    'format_bytes',
    'parse_size',
    'safe_filename',
    'is_video_file',
    'is_media_file',
]
