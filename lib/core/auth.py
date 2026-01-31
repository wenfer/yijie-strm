"""
认证 Provider 接口

定义统一的认证流程抽象
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from ..core.models import AuthToken, QRCodeAuth
from ..core.exceptions import AuthenticationError


class AuthProvider(ABC):
    """认证提供者接口

    定义统一的认证流程，支持多种认证方式：
    - 二维码扫码认证
    - 设备码认证
    - 用户名密码认证
    - OAuth 2.0 认证
    """

    @abstractmethod
    def get_qrcode(self) -> QRCodeAuth:
        """获取二维码认证信息

        Returns:
            QRCodeAuth: 二维码信息（包含 URL、会话 ID 等）

        Raises:
            AuthenticationError: 获取二维码失败
        """
        pass

    @abstractmethod
    def check_qrcode_status(self, session_id: str) -> int:
        """检查二维码扫描状态

        Args:
            session_id: 会话 ID

        Returns:
            int: 状态码
                0 - 未扫描
                1 - 已扫描未确认
                2 - 已确认

        Raises:
            AuthenticationError: 检查状态失败
        """
        pass

    @abstractmethod
    def exchange_token(self, session_id: str, **kwargs) -> AuthToken:
        """交换认证令牌

        Args:
            session_id: 会话 ID
            **kwargs: 额外参数（如 code_verifier 等）

        Returns:
            AuthToken: 访问令牌

        Raises:
            AuthenticationError: 令牌交换失败
        """
        pass

    @abstractmethod
    def refresh_token(self, token: AuthToken) -> AuthToken:
        """刷新访问令牌

        Args:
            token: 当前令牌

        Returns:
            AuthToken: 新令牌

        Raises:
            AuthenticationError: 刷新失败
        """
        pass

    @abstractmethod
    def save_token(self, token: AuthToken, file_path: str) -> None:
        """保存令牌到文件

        Args:
            token: 令牌对象
            file_path: 保存路径

        Raises:
            IOError: 保存失败
        """
        pass

    @abstractmethod
    def load_token(self, file_path: str) -> Optional[AuthToken]:
        """从文件加载令牌

        Args:
            file_path: 令牌文件路径

        Returns:
            Optional[AuthToken]: 令牌对象，文件不存在返回 None

        Raises:
            AuthenticationError: 令牌无效
        """
        pass

    def validate_token(self, token: AuthToken) -> bool:
        """验证令牌有效性

        Args:
            token: 令牌对象

        Returns:
            bool: 是否有效
        """
        # 默认实现：检查是否过期
        return not token.is_expired()

    def auto_refresh_token(
        self,
        file_path: str,
        on_refresh: Optional[Callable[[AuthToken], None]] = None
    ) -> AuthToken:
        """智能获取令牌（自动刷新策略）

        优先级：
        1. 从文件加载有效令牌
        2. 刷新过期令牌
        3. 重新认证

        Args:
            file_path: 令牌文件路径
            on_refresh: 刷新成功后的回调函数

        Returns:
            AuthToken: 有效令牌

        Raises:
            AuthenticationError: 所有方式都失败
        """
        # 1. 尝试加载现有令牌
        token = self.load_token(file_path)

        if token and self.validate_token(token):
            return token

        # 2. 尝试刷新
        if token and token.refresh_token:
            try:
                new_token = self.refresh_token(token)
                self.save_token(new_token, file_path)
                if on_refresh:
                    on_refresh(new_token)
                return new_token
            except AuthenticationError:
                pass

        # 3. 需要重新认证
        raise AuthenticationError(
            "Token expired or invalid, please re-authenticate"
        )


class TokenWatcher:
    """令牌自动续期守护线程

    在令牌即将过期前自动刷新
    """

    def __init__(
        self,
        auth_provider: AuthProvider,
        token_file: str,
        refresh_buffer: int = 60
    ):
        """
        Args:
            auth_provider: 认证提供者
            token_file: 令牌文件路径
            refresh_buffer: 提前刷新时间（秒）
        """
        self.auth_provider = auth_provider
        self.token_file = token_file
        self.refresh_buffer = refresh_buffer
        self._running = False
        self._thread = None

    def start(self):
        """启动守护线程"""
        if self._running:
            return

        import threading

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止守护线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _watch_loop(self):
        """监控循环"""
        import time

        while self._running:
            try:
                token = self.auth_provider.load_token(self.token_file)
                if token and token.is_expired(self.refresh_buffer):
                    # 提前刷新
                    new_token = self.auth_provider.refresh_token(token)
                    self.auth_provider.save_token(new_token, self.token_file)
            except Exception:
                pass  # 忽略错误，继续监控

            time.sleep(30)  # 每 30 秒检查一次
