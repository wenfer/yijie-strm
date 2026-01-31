"""
115 网盘 Provider

导出 Provider115 并自动注册到工厂
"""
from .provider import Provider115
from .auth import Auth115
from .client import Client115
from .config import Config115, default_config
from ..factory import provider_factory

# 自动注册到工厂
provider_factory.register("115", Provider115)

__all__ = [
    "Provider115",
    "Auth115",
    "Client115",
    "Config115",
    "default_config",
]
