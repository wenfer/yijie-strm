"""
115 网盘 API 客户端

封装 115 API 调用细节，不涉及认证逻辑
"""
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any

import requests

from .config import Config115, default_config

logger = logging.getLogger(__name__)


class RateLimiter:
    """API 请求速率限制器"""

    def __init__(self, rps: int):
        self.rps = rps
        self.interval = 1.0 / rps
        self.last_call = 0
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_call = time.time()


class Client115:
    """115 网盘 API 客户端（纯 API 调用层）

    不包含认证逻辑，由调用方提供 access_token
    """

    def __init__(self, config: Config115 = None):
        self.config = config or default_config
        self._rate_limiter = RateLimiter(self.config.API_RPS_LIMIT)

    def request(
        self,
        url: str,
        access_token: str,
        method: str = 'GET',
        params: Dict = None,
        data: Dict = None,
        retry_count: int = 3
    ) -> Optional[Dict]:
        """发送 API 请求

        Args:
            url: API URL
            access_token: 访问令牌
            method: HTTP 方法
            params: 查询参数
            data: POST 数据
            retry_count: 重试次数

        Returns:
            API 响应字典，失败返回 None
        """
        for attempt in range(retry_count):
            self._rate_limiter.acquire()
            result = self._call_api(url, access_token, method, params, data)

            if result is None:
                if attempt < retry_count - 1:
                    logger.warning(f"client.py:68 - Attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.1 * (attempt + 1))
                    continue
                logger.error(f"client.py:71 - API request to {url} failed after {retry_count} attempts")
                return None

            if result.get("state"):
                return result
            else:
                error_message = result.get('message', 'Unknown API error')
                logger.error(f"client.py:78 - 115 API error {url}: {error_message}")
                return result

        return None

    def _call_api(
        self,
        url: str,
        access_token: str,
        method: str,
        params: Dict,
        data: Dict
    ) -> Optional[Dict]:
        """执行 API 调用"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": self.config.USER_AGENT,
            "Referer": self.config.REFERER_DOMAIN
        }

        if method == 'POST':
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            if data:
                data = {k: v for k, v in data.items() if v is not None}

        try:
            timeout = (self.config.DEFAULT_CONNECT_TIMEOUT, self.config.DEFAULT_READ_TIMEOUT)

            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=data, timeout=timeout)
            else:
                logger.error(f"client.py:118 - Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()

            if not response.text.strip():
                logger.error(f"client.py:124 - Empty response from {url}")
                return None

            return response.json()

        except requests.exceptions.Timeout:
            logger.warning(f"client.py:130 - Request to {url} timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"client.py:133 - Network error during call to {url}: {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"client.py:136 - JSON decode error for {url}")
            return None

    # ==================== 文件列表 API ====================

    def list_files(
        self,
        access_token: str,
        cid: str,
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Tuple[List[Dict], int]:
        """获取目录下的文件列表"""
        params = {
            "cid": cid,
            "limit": limit,
            "offset": offset,
            **self.config.COMMON_BROWSE_PARAMS,
            **kwargs
        }

        result = self.request(
            self.config.FILE_LIST_API_URL,
            access_token,
            'GET',
            params
        )

        if result and isinstance(result.get("data"), list):
            return result["data"], result.get("count", 0)
        return [], 0

    def list_all_files(
        self,
        access_token: str,
        cid: str,
        **kwargs
    ) -> List[Dict]:
        """获取目录下的所有文件（自动分页）"""
        first_page, total = self.list_files(
            access_token, cid,
            limit=self.config.API_FETCH_LIMIT,
            offset=0,
            **kwargs
        )

        if total <= self.config.API_FETCH_LIMIT:
            return first_page

        all_items = list(first_page)
        offsets = list(range(self.config.API_FETCH_LIMIT, total, self.config.API_FETCH_LIMIT))

        with ThreadPoolExecutor(max_workers=self.config.API_CONCURRENT_THREADS) as executor:
            futures = {
                executor.submit(
                    self.list_files,
                    access_token, cid,
                    self.config.API_FETCH_LIMIT,
                    offset,
                    **kwargs
                ): offset
                for offset in offsets
            }
            for future in as_completed(futures):
                try:
                    items, _ = future.result()
                    all_items.extend(items)
                except Exception as e:
                    logger.error(f"client.py:209 - Error fetching page: {e}")

        return all_items

    # ==================== 搜索 API ====================

    def search(
        self,
        access_token: str,
        keyword: str,
        cid: str = '0',
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Tuple[List[Dict], int]:
        """搜索文件"""
        params = {
            "search_value": keyword,
            "cid": cid,
            "limit": limit,
            "offset": offset,
            **kwargs
        }

        result = self.request(
            self.config.SEARCH_API_URL,
            access_token,
            'GET',
            params
        )

        if result and isinstance(result.get("data"), list):
            return result["data"], result.get("count", 0)
        return [], 0

    # ==================== 下载链接 API ====================

    def get_download_url(self, access_token: str, pick_code: str) -> Optional[str]:
        """获取文件下载链接"""
        data = {"pick_code": pick_code}
        result = self.request(
            self.config.DOWNLOAD_API_URL,
            access_token,
            'POST',
            data=data
        )

        if not result:
            return None

        data_payload = result.get('data')
        if isinstance(data_payload, dict):
            for pc_key, pc_data in data_payload.items():
                if isinstance(pc_data, dict) and 'url' in pc_data:
                    url_obj = pc_data['url']
                    if isinstance(url_obj, dict) and url_obj.get('url'):
                        return url_obj['url']

        logger.warning(f"client.py:274 - Could not extract download URL for pick_code: {pick_code}")
        return None

    # ==================== 文件夹信息 API ====================

    def get_item_info(self, access_token: str, file_id: str) -> Optional[Dict]:
        """获取文件/文件夹详细信息"""
        params = {"file_id": file_id}
        result = self.request(
            self.config.GET_FOLDER_INFO_API_URL,
            access_token,
            'GET',
            params=params
        )

        if result and result.get("state") and isinstance(result.get("data"), dict):
            return result["data"]
        return None

    # ==================== 文件操作 API ====================

    def create_folder(
        self,
        access_token: str,
        parent_id: str,
        folder_name: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """创建文件夹，返回 (folder_id, folder_name, error_message)"""
        data = {"pid": parent_id, "file_name": folder_name}
        result = self.request(
            self.config.ADD_FOLDER_API_URL,
            access_token,
            'POST',
            data=data
        )

        if result and result.get("state") and isinstance(result.get("data"), dict):
            data = result["data"]
            return data.get("file_id"), data.get("file_name"), None

        error = result.get('message', 'Unknown error') if result else "API request failed"
        return None, None, error

    def rename(
        self,
        access_token: str,
        file_id: str,
        new_name: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """重命名文件/文件夹，返回 (success, new_name, error_message)"""
        data = {"file_id": file_id, "file_name": new_name}
        result = self.request(
            self.config.UPDATE_FILE_API_URL,
            access_token,
            'POST',
            data=data
        )

        if result and result.get("state"):
            updated_name = result.get("data", {}).get("file_name", new_name)
            return True, updated_name, None

        error = result.get('message', 'Unknown error') if result else "API request failed"
        return False, None, error

    def move(
        self,
        access_token: str,
        file_ids: List[str],
        to_cid: str
    ) -> bool:
        """移动文件/文件夹"""
        if not file_ids:
            return False

        data = {
            "file_ids": ",".join(file_ids),
            "to_cid": to_cid
        }
        result = self.request(
            self.config.MOVE_API_URL,
            access_token,
            'POST',
            data=data
        )
        return bool(result and result.get("state"))

    def delete(
        self,
        access_token: str,
        file_ids: List[str],
        parent_id: str = None
    ) -> Tuple[bool, Optional[str]]:
        """删除文件/文件夹，返回 (success, error_message)"""
        if not file_ids:
            return False, "No file IDs provided"

        data = {"file_ids": ",".join(file_ids)}
        if parent_id:
            data["parent_id"] = parent_id

        result = self.request(
            self.config.DELETE_FILE_API_URL,
            access_token,
            'POST',
            data=data
        )

        if result and result.get("state"):
            return True, None

        error = result.get("message", "Unknown error") if result else "API request failed"
        return False, error

    # ==================== 事件监听 API ====================

    def get_life_behavior_list(
        self,
        access_token: str,
        type: str = "",
        date: str = "",
        limit: int = 1000,
        offset: int = 0
    ) -> Optional[Dict]:
        """获取生活操作事件列表

        Args:
            access_token: 访问令牌
            type: 事件类型
            date: 日期 YYYY-MM-DD
            limit: 每页数量
            offset: 偏移量

        Returns:
            包含事件列表的字典，格式: {"count": int, "list": [events]}
        """
        params = {
            "type": type,
            "date": date,
            "limit": limit,
            "offset": offset
        }
        params = {k: v for k, v in params.items() if v}

        result = self.request(
            self.config.LIFE_BEHAVIOR_API_URL,
            access_token,
            'GET',
            params
        )

        if result and result.get("state") and isinstance(result.get("data"), dict):
            return result["data"]
        return None
