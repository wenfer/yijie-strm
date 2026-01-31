"""
Provider 工厂

负责创建不同类型的 Provider 实例
"""

from typing import Dict, Type, Optional
from ..core.provider import CloudStorageProvider
from ..core.exceptions import ProviderNotSupportedError


class ProviderFactory:
    """Provider 工厂类"""

    _providers: Dict[str, Type[CloudStorageProvider]] = {}

    @classmethod
    def register(cls, provider_type: str, provider_class: Type[CloudStorageProvider]):
        """注册 Provider

        Args:
            provider_type: Provider 类型（如 "115", "aliyun"）
            provider_class: Provider 类
        """
        cls._providers[provider_type] = provider_class

    @classmethod
    def create(
        cls,
        provider_type: str,
        token_file: str,
        **kwargs
    ) -> CloudStorageProvider:
        """创建 Provider 实例

        Args:
            provider_type: Provider 类型
            token_file: 令牌文件路径
            **kwargs: 额外参数

        Returns:
            CloudStorageProvider: Provider 实例

        Raises:
            ProviderNotSupportedError: 不支持的 Provider 类型
        """
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            raise ProviderNotSupportedError(
                f"Provider type '{provider_type}' is not supported. "
                f"Available types: {list(cls._providers.keys())}"
            )

        return provider_class(token_file=token_file, **kwargs)

    @classmethod
    def get_supported_types(cls) -> list:
        """获取支持的 Provider 类型列表

        Returns:
            list: Provider 类型列表
        """
        return list(cls._providers.keys())


# 工厂单例
provider_factory = ProviderFactory()
