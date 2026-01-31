"""
115 网盘认证实现

实现 AuthProvider 接口，支持设备码认证（扫码登录）
"""
import base64
import hashlib
import json
import logging
import os
import secrets
import string
import time
from typing import Optional

import requests

from ...core.auth import AuthProvider
from ...core.models import AuthToken, QRCodeAuth
from ...core.exceptions import AuthenticationError, InvalidTokenError
from .config import Config115, default_config

logger = logging.getLogger(__name__)


class Auth115(AuthProvider):
    """115 网盘认证提供者

    基于 OAuth 2.0 + PKCE 的设备码认证
    """

    def __init__(self, config: Config115 = None):
        self.config = config or default_config

    def get_qrcode(self) -> QRCodeAuth:
        """获取二维码认证信息"""
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        try:
            response = requests.post(
                self.config.AUTH_DEVICE_CODE_URL,
                data={
                    "client_id": self.config.get_client_id(4),
                    "code_challenge": code_challenge,
                    "code_challenge_method": "sha256"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=(self.config.DEFAULT_CONNECT_TIMEOUT, self.config.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()
            auth_data = response.json()

            if auth_data.get("code") != 0 or "data" not in auth_data:
                raise AuthenticationError(f"Failed to get device code: {auth_data}")

            data = auth_data["data"]
            if not all(k in data for k in ("uid", "qrcode", "time", "sign")):
                raise AuthenticationError("Device code response missing required fields")

            # 保存 code_verifier（后续交换 Token 需要）
            self._code_verifier = code_verifier

            return QRCodeAuth(
                qrcode_url=data["qrcode"],
                session_id=data["uid"],
                expires_at=time.time() + 300,  # 假设 5 分钟过期
                raw_data={
                    "uid": data["uid"],
                    "time": data["time"],
                    "sign": data["sign"],
                    "code_verifier": code_verifier
                }
            )

        except requests.RequestException as e:
            logger.error(f"auth.py:58 - Failed to get QR code: {e}")
            raise AuthenticationError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"auth.py:61 - Invalid JSON response: {e}")
            raise AuthenticationError("Invalid API response")

    def check_qrcode_status(self, session_id: str) -> int:
        """检查二维码扫描状态

        Args:
            session_id: QRCodeAuth.raw_data 中的完整信息

        Returns:
            0: 未扫描
            1: 已扫描未确认
            2: 已确认
        """
        # session_id 实际上是 uid，需要从 raw_data 获取完整参数
        # 这里为了简化接口，我们将 uid 作为 session_id
        # 实际使用时需要传入 raw_data
        raise NotImplementedError(
            "Please use check_qrcode_status_with_params instead"
        )

    def check_qrcode_status_with_params(
        self, uid: str, time_val: str, sign: str
    ) -> int:
        """检查二维码扫描状态（带完整参数）

        Args:
            uid: 设备 UID
            time_val: 时间戳
            sign: 签名

        Returns:
            0: 未扫描/未知
            1: 未扫描
            2: 已扫描
        """
        try:
            response = requests.get(
                self.config.QRCODE_STATUS_URL,
                params={"uid": uid, "time": time_val, "sign": sign},
                timeout=(self.config.DEFAULT_CONNECT_TIMEOUT, self.config.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()
            status_data = response.json()

            # 115 API 返回格式: {"data": {"status": 2}}
            status = status_data.get("data", {}).get("status", 0)
            return status

        except Exception as e:
            logger.warning(f"auth.py:112 - Failed to check QR code status: {e}")
            return 0

    def exchange_token(self, session_id: str, **kwargs) -> AuthToken:
        """交换认证令牌

        Args:
            session_id: uid
            **kwargs: 必须包含 code_verifier
        """
        code_verifier = kwargs.get("code_verifier")
        if not code_verifier:
            raise AuthenticationError("code_verifier is required")

        try:
            response = requests.post(
                self.config.DEVICE_CODE_TO_TOKEN_URL,
                data={"uid": session_id, "code_verifier": code_verifier},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=(self.config.DEFAULT_CONNECT_TIMEOUT, self.config.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()
            token_data = response.json()

            if token_data.get("code") != 0 or "data" not in token_data:
                raise AuthenticationError(f"Failed to exchange token: {token_data}")

            data = token_data["data"]
            expires_in = data.get("expires_in", 7200)

            return AuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_at=time.time() + expires_in,
                token_type="Bearer",
                raw_data=data
            )

        except requests.RequestException as e:
            logger.error(f"auth.py:155 - Failed to exchange token: {e}")
            raise AuthenticationError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"auth.py:158 - Invalid JSON response: {e}")
            raise AuthenticationError("Invalid API response")

    def refresh_token(self, token: AuthToken) -> AuthToken:
        """刷新访问令牌"""
        if not token.refresh_token:
            raise AuthenticationError("No refresh_token available")

        try:
            response = requests.post(
                self.config.REFRESH_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"refresh_token": token.refresh_token},
                timeout=(self.config.DEFAULT_CONNECT_TIMEOUT, self.config.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()

            if not response.text.strip():
                raise AuthenticationError("Empty response from refresh API")

            result = response.json()
            if result.get("code") != 0 or "data" not in result:
                raise AuthenticationError(
                    f"Token refresh failed: {result.get('message', 'Unknown error')}"
                )

            data = result["data"]
            expires_in = data.get("expires_in", 7200)

            return AuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", token.refresh_token),
                expires_at=time.time() + expires_in,
                token_type="Bearer",
                raw_data=data
            )

        except requests.RequestException as e:
            logger.error(f"auth.py:196 - Token refresh network error: {e}")
            raise AuthenticationError(f"Network error: {e}")
        except json.JSONDecodeError:
            logger.error(f"auth.py:199 - Invalid JSON response from refresh API")
            raise AuthenticationError("Invalid API response")

    def save_token(self, token: AuthToken, file_path: str) -> None:
        """保存令牌到文件

        使用 115 特定的 JSON 格式
        """
        # 确保目录存在
        token_dir = os.path.dirname(file_path)
        if token_dir and not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)

        json_data = {
            "timestamp": int(time.time()),
            "state": 1,
            "code": 0,
            "message": "",
            "data": {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token or "",
                "expires_in": int(token.expires_at - time.time()) if token.expires_at else 7200,
                "user_id": token.raw_data.get("user_id", "") if token.raw_data else ""
            }
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            logger.info(f"auth.py:232 - Token saved to {file_path}")
        except IOError as e:
            logger.error(f"auth.py:234 - Error saving token: {e}")
            raise

    def load_token(self, file_path: str) -> Optional[AuthToken]:
        """从文件加载令牌"""
        if not os.path.exists(file_path):
            logger.debug(f"auth.py:241 - Token file not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                token_container = json.load(f)

            if not isinstance(token_container, dict) or "data" not in token_container:
                raise InvalidTokenError("Invalid token file format")

            data = token_container["data"]
            timestamp = token_container.get("timestamp", 0)
            expires_in = data.get("expires_in", 7200)
            expire_timestamp = timestamp + expires_in

            return AuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_at=expire_timestamp,
                token_type="Bearer",
                raw_data=data
            )

        except json.JSONDecodeError as e:
            logger.error(f"auth.py:266 - Invalid JSON in token file: {e}")
            raise InvalidTokenError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"auth.py:269 - Error reading token file: {e}")
            raise InvalidTokenError(f"Failed to load token: {e}")

    def _generate_code_verifier(self, length: int = 128) -> str:
        """生成 PKCE code_verifier"""
        allowed_chars = string.ascii_letters + string.digits + '-._~'
        return ''.join(secrets.choice(allowed_chars) for _ in range(length))

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """生成 PKCE code_challenge"""
        sha256 = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256).rstrip(b'=').decode('ascii')
