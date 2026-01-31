"""
全局配置模块

从环境变量加载配置
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GatewayConfig:
    """网关服务配置"""
    HOST: str = "0.0.0.0"
    PORT: int = 8115
    DEBUG: bool = False
    STRM_BASE_URL: Optional[str] = None
    CACHE_TTL: int = 3600  # 下载链接缓存时间（秒）
    ENABLE_CORS: bool = True  # 是否启用 CORS

    @classmethod
    def from_env(cls) -> 'GatewayConfig':
        """从环境变量加载配置"""
        return cls(
            HOST=os.getenv("GATEWAY_HOST", "0.0.0.0"),
            PORT=int(os.getenv("GATEWAY_PORT", "8115")),
            DEBUG=os.getenv("GATEWAY_DEBUG", "false").lower() in ("true", "1", "yes"),
            STRM_BASE_URL=os.getenv("STRM_BASE_URL"),
            CACHE_TTL=int(os.getenv("CACHE_TTL", "3600")),
            ENABLE_CORS=os.getenv("ENABLE_CORS", "true").lower() in ("true", "1", "yes"),
        )


@dataclass
class DatabaseConfig:
    """数据库配置"""
    TYPE: str = "sqlite"  # sqlite 或 mysql
    PATH: str = "~/.strm_gateway.db"  # SQLite 数据库路径
    HOST: str = "localhost"  # MySQL 主机
    PORT: int = 3306  # MySQL 端口
    NAME: str = "strm_gateway"  # MySQL 数据库名
    USER: str = "root"  # MySQL 用户名
    PASSWORD: str = ""  # MySQL 密码

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """从环境变量加载配置"""
        return cls(
            TYPE=os.getenv("DB_TYPE", "sqlite"),
            PATH=os.getenv("DB_PATH", "~/.strm_gateway.db"),
            HOST=os.getenv("DB_HOST", "localhost"),
            PORT=int(os.getenv("DB_PORT", "3306")),
            NAME=os.getenv("DB_NAME", "strm_gateway"),
            USER=os.getenv("DB_USER", "root"),
            PASSWORD=os.getenv("DB_PASSWORD", ""),
        )


@dataclass
class AppConfig:
    """应用配置"""
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """从环境变量加载配置"""
        return cls(
            gateway=GatewayConfig.from_env(),
            database=DatabaseConfig.from_env(),
        )


# 默认配置实例
default_config = AppConfig.from_env()
