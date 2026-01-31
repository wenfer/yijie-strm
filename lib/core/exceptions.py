"""
通用异常定义
"""


class CloudStorageError(Exception):
    """云存储基础异常"""
    pass


class AuthenticationError(CloudStorageError):
    """认证失败异常"""
    pass


class TokenExpiredError(AuthenticationError):
    """令牌过期异常"""
    pass


class InvalidTokenError(AuthenticationError):
    """无效令牌异常"""
    pass


class FileNotFoundError(CloudStorageError):
    """文件不存在异常"""
    pass


class PermissionDeniedError(CloudStorageError):
    """权限不足异常"""
    pass


class RateLimitExceededError(CloudStorageError):
    """速率限制异常"""
    pass


class NetworkError(CloudStorageError):
    """网络错误异常"""
    pass


class ProviderNotSupportedError(CloudStorageError):
    """不支持的 Provider 异常"""
    pass
