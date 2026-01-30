"""
115 网盘 Token 管理模块
支持设备码认证、Token 刷新、自动续期
使用本地文件存储 Token（无需 rclone）
"""
from __future__ import annotations
import base64
import hashlib
import json
import logging
import os
import secrets
import string
import threading
import time
from typing import Dict, Optional, Callable

import requests

from ..config import AppConfig, default_config

logger = logging.getLogger(__name__)


class TokenManager:
    """Token 管理器 - 负责 OAuth Token 的获取、刷新和持久化"""

    def __init__(self, config: AppConfig = None):
        self.config = config or default_config
        self._refresh_lock = threading.Lock()

    def refresh_and_get_new_token_with_info(self, allow_device_code: bool = True) -> Optional[Dict]:
        """
        刷新 Token 并返回包含过期时间戳的信息

        Args:
            allow_device_code: 是否允许使用设备码认证（扫码），默认 True
        """
        with self._refresh_lock:
            logger.info(f"[TokenManager] Starting token refresh at {time.strftime('%Y-%m-%d %H:%M:%S')}")

            try:
                # 1. 尝试从本地文件加载现有 Token
                loaded_data = self._load_token_from_file()

                if loaded_data:
                    expire_timestamp = loaded_data.get("_expire_timestamp", 0)
                    if time.time() < expire_timestamp:
                        logger.info(f"[TokenManager] Loaded token still valid, expires at: "
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_timestamp))}")
                        return loaded_data

                # 2. 尝试使用 refresh_token 刷新
                if loaded_data and loaded_data.get("refresh_token"):
                    logger.debug("[TokenManager] Attempting API refresh with refresh_token")
                    new_token_data = self._refresh_access_token_from_api(loaded_data["refresh_token"])
                    if new_token_data:
                        timestamp = int(time.time())
                        expires_in = new_token_data.get("expires_in", 7200)
                        new_token_data["_expire_timestamp"] = timestamp + expires_in
                        self._save_token_to_file(new_token_data)
                        logger.info(f"[TokenManager] Token refreshed successfully, expires at: "
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_token_data['_expire_timestamp']))}")
                        return new_token_data

                # 3. 回退到设备码认证（扫码）- 仅在允许时执行
                if allow_device_code:
                    logger.info("[TokenManager] Falling back to device code authentication (QR code)")
                    new_token_data = self._get_new_tokens_via_device_code()
                    if new_token_data:
                        timestamp = int(time.time())
                        expires_in = new_token_data.get("expires_in", 7200)
                        new_token_data["_expire_timestamp"] = timestamp + expires_in
                        self._save_token_to_file(new_token_data)
                        logger.info(f"[TokenManager] New token obtained via device code")
                        return new_token_data
                else:
                    logger.info("[TokenManager] Device code authentication disabled, skipping")

                logger.error("[TokenManager] All token refresh methods failed")
                return None

            except Exception as e:
                logger.exception(f"[TokenManager] Unexpected error during refresh: {e}")
                return None

    def refresh_and_get_new_token(self) -> Optional[str]:
        """刷新并返回新的 access_token"""
        token_info = self.refresh_and_get_new_token_with_info()
        return token_info["access_token"] if token_info else None

    def _load_token_from_file(self) -> Optional[Dict]:
        """从本地文件加载 Token 数据"""
        token_file = self.config.auth.TOKEN_FILE_PATH

        if not os.path.exists(token_file):
            logger.info(f"[TokenManager] Token file not found: {token_file}")
            return None

        try:
            with open(token_file, 'r', encoding='utf-8') as f:
                token_container = json.load(f)

            if isinstance(token_container, dict) and "data" in token_container:
                data = token_container["data"]
                timestamp = token_container.get("timestamp", 0)
                expires_in = data.get("expires_in", 7200)
                expire_timestamp = timestamp + expires_in
                logger.debug(f"[TokenManager] Loaded token from file, expires at: "
                             f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_timestamp))}")
                return {
                    **data,
                    "_expire_timestamp": expire_timestamp
                }
        except json.JSONDecodeError as e:
            logger.error(f"[TokenManager] Invalid JSON in token file: {e}")
        except Exception as e:
            logger.error(f"[TokenManager] Error reading token file: {e}")

        return None

    def _save_token_to_file(self, token_data: dict) -> bool:
        """保存 Token 数据到本地文件"""
        token_file = self.config.auth.TOKEN_FILE_PATH

        # 确保目录存在
        token_dir = os.path.dirname(token_file)
        if token_dir and not os.path.exists(token_dir):
            os.makedirs(token_dir, exist_ok=True)

        json_data = {
            "timestamp": int(time.time()),
            "state": 1,
            "code": 0,
            "message": "",
            "data": {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": token_data.get("expires_in", 7200),
                "user_id": token_data.get("user_id", "")
            }
        }

        try:
            with open(token_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=4, ensure_ascii=False)
            logger.info(f"[TokenManager] Token saved to {token_file}")
            return True
        except Exception as e:
            logger.error(f"[TokenManager] Error saving token: {e}")
            return False

    def _refresh_access_token_from_api(self, refresh_token_value: str) -> Optional[Dict]:
        """使用 refresh_token 调用 API 刷新 access_token"""
        try:
            response = requests.post(
                self.config.auth.REFRESH_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"refresh_token": refresh_token_value},
                timeout=(self.config.network.DEFAULT_CONNECT_TIMEOUT, self.config.network.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()

            if not response.text.strip():
                logger.error("Empty response from refresh API")
                return None

            result = response.json()
            if result.get("code") == 0 and "data" in result:
                return result["data"]

            logger.error(f"Token refresh API error: {result.get('message', 'Unknown error')}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh network error: {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from refresh API")
            return None

    def _get_new_tokens_via_device_code(self, callback: Optional[Callable[[str, Dict], None]] = None) -> Optional[Dict]:
        """
        通过设备码认证获取新 Token（扫码登录）

        Args:
            callback: 可选的回调函数，用于通知二维码信息 callback(qrcode_url, auth_info)
        """
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        def _fetch_json(url, method='post', **kwargs):
            try:
                resp = requests.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, json.JSONDecodeError) as e:
                logger.error(f"API request failed ({url}): {e}")
                return None

        # 获取设备码
        auth_data = _fetch_json(
            self.config.auth.AUTH_DEVICE_CODE_URL,
            data={
                "client_id": self.config.auth.get_client_id(4),
                "code_challenge": code_challenge,
                "code_challenge_method": "sha256"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if not auth_data or auth_data.get("code") != 0 or "data" not in auth_data:
            logger.error(f"Failed to get device code: {auth_data}")
            return None

        data = auth_data["data"]
        if not all(k in data for k in ("uid", "qrcode", "time", "sign")):
            logger.error("Device code response missing required fields")
            return None

        uid, qrcode_content, time_val, sign = data["uid"], data["qrcode"], data["time"], data["sign"]

        # 如果提供了回调函数，通知二维码信息
        if callback:
            callback(qrcode_content, {"uid": uid, "time": time_val, "sign": sign})
        else:
            # 命令行模式：打印二维码 URL
            logger.info("=" * 50)
            logger.info("请使用 115 客户端扫描二维码进行授权:")
            logger.info(f"QR Code URL: {qrcode_content}")
            logger.info("=" * 50)
            logger.info("等待扫码中...")

        # 轮询等待扫码
        while True:
            status_data = _fetch_json(
                self.config.auth.QRCODE_STATUS_URL,
                method='get',
                params={"uid": uid, "time": time_val, "sign": sign}
            )
            if not status_data:
                return None
            if status_data.get("data", {}).get("status") == 2:
                logger.info("扫码成功！正在获取 Token...")
                break
            time.sleep(5)

        # 获取 Token
        token_data = _fetch_json(
            self.config.auth.DEVICE_CODE_TO_TOKEN_URL,
            data={"uid": uid, "code_verifier": code_verifier},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if token_data and token_data.get("code") == 0 and "data" in token_data:
            logger.info("Token 获取成功！")
            return token_data["data"]

        logger.error(f"Failed to get token: {token_data}")
        return None

    def get_qrcode_for_auth(self) -> Optional[Dict]:
        """
        获取用于认证的二维码信息（不阻塞）

        Returns:
            包含二维码 URL 和认证信息的字典，或 None
        """
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        try:
            response = requests.post(
                self.config.auth.AUTH_DEVICE_CODE_URL,
                data={
                    "client_id": self.config.auth.get_client_id(4),
                    "code_challenge": code_challenge,
                    "code_challenge_method": "sha256"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=(self.config.network.DEFAULT_CONNECT_TIMEOUT, self.config.network.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()
            auth_data = response.json()

            if auth_data.get("code") != 0 or "data" not in auth_data:
                logger.error(f"Failed to get device code: {auth_data}")
                return None

            data = auth_data["data"]
            if not all(k in data for k in ("uid", "qrcode", "time", "sign")):
                logger.error("Device code response missing required fields")
                return None

            return {
                "qrcode_url": data["qrcode"],
                "uid": data["uid"],
                "time": data["time"],
                "sign": data["sign"],
                "code_verifier": code_verifier
            }
        except Exception as e:
            logger.error(f"Failed to get QR code: {e}")
            return None

    def check_qrcode_status(self, uid: str, time_val: str, sign: str) -> Optional[Dict]:
        """
        检查二维码扫描状态

        Args:
            uid: 设备 UID
            time_val: 时间戳
            sign: 签名

        Returns:
            状态信息字典，包含 status 字段（1=未扫描, 2=已扫描）
        """
        try:
            response = requests.get(
                self.config.auth.QRCODE_STATUS_URL,
                params={"uid": uid, "time": time_val, "sign": sign},
                timeout=(self.config.network.DEFAULT_CONNECT_TIMEOUT, self.config.network.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to check QR code status: {e}")
            return None

    def exchange_token_with_device_code(self, uid: str, code_verifier: str) -> Optional[Dict]:
        """
        使用设备码交换 Token

        Args:
            uid: 设备 UID
            code_verifier: PKCE code verifier

        Returns:
            Token 数据字典，或 None
        """
        try:
            response = requests.post(
                self.config.auth.DEVICE_CODE_TO_TOKEN_URL,
                data={"uid": uid, "code_verifier": code_verifier},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=(self.config.network.DEFAULT_CONNECT_TIMEOUT, self.config.network.DEFAULT_READ_TIMEOUT)
            )
            response.raise_for_status()
            token_data = response.json()

            if token_data.get("code") == 0 and "data" in token_data:
                # 保存 Token
                timestamp = int(time.time())
                expires_in = token_data["data"].get("expires_in", 7200)
                token_info = {
                    **token_data["data"],
                    "_expire_timestamp": timestamp + expires_in
                }
                self._save_token_to_file(token_info)
                logger.info("Token 获取并保存成功！")
                return token_info

            logger.error(f"Failed to exchange token: {token_data}")
            return None
        except Exception as e:
            logger.error(f"Failed to exchange token: {e}")
            return None

    def _generate_code_verifier(self, length: int = 128) -> str:
        """生成 PKCE code_verifier"""
        allowed_chars = string.ascii_letters + string.digits + '-._~'
        return ''.join(secrets.choice(allowed_chars) for _ in range(length))

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """生成 PKCE code_challenge"""
        sha256 = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256).rstrip(b'=').decode('ascii')


class TokenWatcher:
    """Token 守护线程 - 自动监控和刷新 Token"""

    def __init__(self, token_manager: TokenManager, on_token_refresh: Callable[[str], None] = None):
        self.token_manager = token_manager
        self.on_token_refresh = on_token_refresh

        self._current_token: Optional[str] = None
        self._token_expire_timestamp: float = 0.0
        self._token_valid_event = threading.Event()
        self._stop_event = threading.Event()
        self._watcher_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """
        启动 Token 守护线程

        注意：启动时不会触发扫码认证，只会尝试从文件加载或刷新已有 token
        """
        # 初始化 Token（不允许设备码认证，避免启动时阻塞）
        token_info = self.token_manager.refresh_and_get_new_token_with_info(allow_device_code=False)
        if token_info:
            self._current_token = token_info["access_token"]
            self._token_expire_timestamp = token_info["_expire_timestamp"]
            self._token_valid_event.set()
            logger.info(f"[TokenWatcher] Token initialized, expires at: "
                        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._token_expire_timestamp))}")
        else:
            logger.warning("[TokenWatcher] No valid token found, please authenticate via API")
            return False

        # 启动守护线程
        self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()
        return True

    def stop(self):
        """停止 Token 守护线程"""
        self._stop_event.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=2)

    def get_token(self, timeout: float = 60) -> Optional[str]:
        """获取当前有效的 Token"""
        if not self._token_valid_event.wait(timeout=timeout):
            logger.error("[TokenWatcher] Timeout waiting for valid token")
            return None
        return self._current_token

    def is_token_valid(self) -> bool:
        """检查 Token 是否有效"""
        return self._token_valid_event.is_set()

    def _watch_loop(self):
        """Token 监控循环"""
        while not self._stop_event.is_set():
            try:
                now = time.time()
                # 提前 20 秒刷新
                if self._token_expire_timestamp > 0 and now >= (self._token_expire_timestamp - 20):
                    logger.info("[TokenWatcher] Token expiring soon, pausing API calls")
                    self._token_valid_event.clear()

                    # 等待 Token 过期
                    sleep_until = self._token_expire_timestamp + 2
                    while time.time() < sleep_until and not self._stop_event.is_set():
                        time.sleep(0.5)

                    # 刷新 Token
                    logger.info("[TokenWatcher] Refreshing token")
                    new_token_info = self.token_manager.refresh_and_get_new_token_with_info()
                    if new_token_info and new_token_info.get("access_token"):
                        self._current_token = new_token_info["access_token"]
                        self._token_expire_timestamp = new_token_info["_expire_timestamp"]
                        self._token_valid_event.set()

                        if self.on_token_refresh:
                            self.on_token_refresh(self._current_token)

                        logger.info(f"[TokenWatcher] Token refreshed, expires at: "
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._token_expire_timestamp))}")
                    else:
                        logger.error("[TokenWatcher] Token refresh failed")
                        time.sleep(10)
                        continue

                time.sleep(20)
            except Exception as e:
                logger.exception(f"[TokenWatcher] Error: {e}")
                time.sleep(5)
