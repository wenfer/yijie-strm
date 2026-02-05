"""
全局配置模块

使用 Pydantic Settings 管理配置
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    # Tortoise ORM 数据库 URL
    # SQLite: sqlite://db.sqlite3
    # MySQL: mysql://user:password@localhost:3306/dbname
    url: str = Field(default="sqlite://~/.strm_gateway.db", alias="DB_URL")
    
    # 是否生成数据库表结构
    generate_schemas: bool = Field(default=True, alias="DB_GENERATE_SCHEMAS")
    
    # 连接池配置（仅 MySQL 有效）
    min_size: int = Field(default=1, alias="DB_POOL_MIN")
    max_size: int = Field(default=10, alias="DB_POOL_MAX")


class GatewaySettings(BaseSettings):
    """网关服务配置"""
    model_config = SettingsConfigDict(env_prefix="GATEWAY_")
    
    host: str = Field(default="0.0.0.0", alias="GATEWAY_HOST")
    port: int = Field(default=8115, alias="GATEWAY_PORT")
    debug: bool = Field(default=False, alias="GATEWAY_DEBUG")
    
    # STRM 文件基础 URL
    strm_base_url: Optional[str] = Field(default=None, alias="STRM_BASE_URL")
    
    # 下载链接缓存时间（秒）
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")
    
    # CORS 配置
    enable_cors: bool = Field(default=True, alias="ENABLE_CORS")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")


class LogSettings(BaseSettings):
    """日志配置"""
    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        alias="LOG_FORMAT"
    )


class SecuritySettings(BaseSettings):
    """安全认证配置"""
    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    # 管理员账号
    username: str = Field(default="admin", alias="ADMIN_USERNAME")
    # 管理员密码（未配置时自动生成）
    password: Optional[str] = Field(default=None, alias="ADMIN_PASSWORD")
    # JWT 密钥（未配置时自动生成）
    secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    # JWT 算法
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # Token 过期时间（分钟）
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRE_MINUTES")  # 默认7天


class Settings(BaseSettings):
    """应用配置"""

    # 数据库配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # 网关配置
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)

    # 日志配置
    log: LogSettings = Field(default_factory=LogSettings)

    # 安全配置
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # 数据目录
    data_dir: Path = Field(default=Path.home() / ".strm_gateway", alias="DATA_DIR")


@lru_cache
def get_settings() -> Settings:
    """获取配置实例（缓存）"""
    return Settings()
