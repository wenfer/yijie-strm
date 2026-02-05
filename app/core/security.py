"""
安全认证工具模块（简化版）
"""
import logging
import secrets
from typing import Optional

from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# 全局存储管理员凭据
_admin_username: str = "admin"
_admin_password: str = ""


def generate_random_password(length: int = 12) -> str:
    """生成随机密码"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def set_admin_credentials(username: str, password: str):
    """设置管理员凭据"""
    global _admin_username, _admin_password
    _admin_username = username
    _admin_password = password


def verify_credentials(username: str, password: str) -> bool:
    """验证用户名密码"""
    return username == _admin_username and password == _admin_password


def initialize_security(username: str, password: Optional[str]) -> tuple[str, str]:
    """
    初始化安全配置
    返回: (username, password)
    """
    global _admin_username, _admin_password

    _admin_username = username

    if not password:
        password = generate_random_password()
        logger.info("=" * 60)
        logger.info("安全警告: 未配置管理员密码，已生成随机密码")
        logger.info(f"用户名: {username}")
        logger.info(f"密码: {password}")
        logger.info("=" * 60)

    _admin_password = password
    return _admin_username, _admin_password


# 简单的 session 存储（内存中）
_sessions: set = set()


def create_session() -> str:
    """创建 session"""
    session_id = secrets.token_urlsafe(32)
    _sessions.add(session_id)
    return session_id


def verify_session(session_id: Optional[str]) -> bool:
    """验证 session"""
    if not session_id:
        return False
    return session_id in _sessions


def delete_session(session_id: str):
    """删除 session"""
    _sessions.discard(session_id)


async def require_auth(request: Request):
    """检查是否已登录"""
    session_id = request.cookies.get("session_id")
    if not verify_session(session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )
