"""
异常定义模块
"""
from fastapi import HTTPException, status


class AppException(HTTPException):
    """应用基础异常"""
    
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=message)
        self.message = message


class AuthenticationError(AppException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class TokenExpiredError(AuthenticationError):
    """Token 过期错误"""
    
    def __init__(self, message: str = "Token 已过期"):
        super().__init__(message)


class NotFoundError(AppException):
    """资源不存在错误"""
    
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class DriveNotFoundError(NotFoundError):
    """网盘不存在错误"""
    
    def __init__(self, drive_id: str = None):
        message = f"网盘不存在: {drive_id}" if drive_id else "网盘不存在"
        super().__init__(message)


class TaskNotFoundError(NotFoundError):
    """任务不存在错误"""
    
    def __init__(self, task_id: str = None):
        message = f"任务不存在: {task_id}" if task_id else "任务不存在"
        super().__init__(message)


class ValidationError(AppException):
    """参数验证错误"""
    
    def __init__(self, message: str = "参数验证失败"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class ConflictError(AppException):
    """资源冲突错误"""
    
    def __init__(self, message: str = "资源已存在"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ServiceUnavailableError(AppException):
    """服务不可用错误"""
    
    def __init__(self, message: str = "服务暂时不可用"):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
