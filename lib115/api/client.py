"""
115 网盘核心 API 客户端
提供文件列表、搜索、下载链接等核心功能
"""
from __future__ import annotations
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Union, Optional, Any
from urllib.parse import urlencode

import requests

from ..config import AppConfig, default_config
from ..auth.token_manager import TokenManager, TokenWatcher

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
    """115 网盘 API 客户端"""

    def __init__(self, config: AppConfig = None, auto_start_watcher: bool = True):
        self.config = config or default_config
        self.token_manager = TokenManager(self.config)
        self.token_watcher = TokenWatcher(self.token_manager)
        self._rate_limiter = RateLimiter(self.config.network.API_RPS_LIMIT)

        if auto_start_watcher:
            if not self.token_watcher.start():
                raise RuntimeError("Failed to initialize token")

    def close(self):
        """关闭客户端，停止 Token 守护线程"""
        self.token_watcher.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 核心 API 方法 ====================

    def request(self, url: str, method: str = 'GET', params: Dict = None,
                data: Dict = None, retry_count: int = 3) -> Optional[Dict]:
        """发送 API 请求"""
        token = self.token_watcher.get_token(timeout=60)
        if not token:
            logger.error("No valid token available")
            return None

        for attempt in range(retry_count):
            self._rate_limiter.acquire()
            result = self._call_api(url, method, params, data, token)

            if result is None:
                if attempt < retry_count - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.1 * (attempt + 1))
                    continue
                logger.error(f"API request to {url} failed after {retry_count} attempts")
                return None

            if result.get("state"):
                return result
            else:
                error_message = result.get('message', 'Unknown API error')
                logger.error(f"115 API error {url}: {error_message}")
                return result

        return None

    def _call_api(self, url: str, method: str, params: Dict, data: Dict, token: str) -> Optional[Dict]:
        """执行 API 调用"""
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.config.network.USER_AGENT,
            "Referer": self.config.network.REFERER_DOMAIN
        }

        if method == 'POST':
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            if data:
                data = self._build_api_params(data)

        try:
            timeout = (self.config.network.DEFAULT_CONNECT_TIMEOUT,
                       self.config.network.DEFAULT_READ_TIMEOUT)

            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=data, timeout=timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()

            if not response.text.strip():
                logger.error(f"Empty response from {url}")
                return None

            return response.json()

        except requests.exceptions.Timeout:
            logger.warning(f"Request to {url} timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error during call to {url}: {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"JSON decode error for {url}")
            return None

    def _build_api_params(self, base_params: Dict, **kwargs) -> Dict:
        """构建 API 参数"""
        combined = base_params.copy()
        combined.update(kwargs)
        return {k: v for k, v in combined.items() if v is not None}

    # ==================== 文件列表 API ====================

    def list_files(self, cid: str, limit: int = 100, offset: int = 0,
                   **kwargs) -> Tuple[List[Dict], int]:
        """获取目录下的文件列表"""
        params = self._build_api_params({
            "cid": cid,
            "limit": limit,
            "offset": offset,
            **self.config.COMMON_BROWSE_FETCH_PARAMS
        }, **kwargs)

        result = self.request(self.config.api.FILE_LIST_API_URL, 'GET', params)
        if result and isinstance(result.get("data"), list):
            return result["data"], result.get("count", 0)
        return [], 0

    def list_all_files(self, cid: str, **kwargs) -> List[Dict]:
        """获取目录下的所有文件（自动分页）"""
        first_page, total = self.list_files(cid, limit=self.config.API_FETCH_LIMIT, offset=0, **kwargs)
        if total <= self.config.API_FETCH_LIMIT:
            return first_page

        all_items = list(first_page)
        offsets = list(range(self.config.API_FETCH_LIMIT, total, self.config.API_FETCH_LIMIT))

        with ThreadPoolExecutor(max_workers=self.config.network.API_CONCURRENT_THREADS) as executor:
            futures = {
                executor.submit(self.list_files, cid, self.config.API_FETCH_LIMIT, offset, **kwargs): offset
                for offset in offsets
            }
            for future in as_completed(futures):
                try:
                    items, _ = future.result()
                    all_items.extend(items)
                except Exception as e:
                    logger.error(f"Error fetching page: {e}")

        return all_items

    # ==================== 搜索 API ====================

    def search(self, keyword: str, cid: str = '0', limit: int = 100,
               offset: int = 0, **kwargs) -> Tuple[List[Dict], int]:
        """搜索文件"""
        params = self._build_api_params({
            "search_value": keyword,
            "cid": cid,
            "limit": limit,
            "offset": offset
        }, **kwargs)

        result = self.request(self.config.api.SEARCH_API_URL, 'GET', params)
        if result and isinstance(result.get("data"), list):
            return result["data"], result.get("count", 0)
        return [], 0

    # ==================== 下载链接 API ====================

    def get_download_url(self, pick_code: str) -> Optional[str]:
        """获取文件下载链接"""
        data = self._build_api_params({"pick_code": pick_code})
        result = self.request(self.config.api.DOWNLOAD_API_URL, 'POST', data=data)

        if not result:
            return None

        data_payload = result.get('data')
        if isinstance(data_payload, dict):
            for pc_key, pc_data in data_payload.items():
                if isinstance(pc_data, dict) and 'url' in pc_data:
                    url_obj = pc_data['url']
                    if isinstance(url_obj, dict) and url_obj.get('url'):
                        return url_obj['url']

        logger.warning(f"Could not extract download URL for pick_code: {pick_code}")
        return None

    def get_download_url_from_item(self, item: Dict) -> Optional[str]:
        """从文件项获取下载链接"""
        pick_code = item.get("pc") or item.get("pick_code")
        if not pick_code:
            logger.warning("Item missing pick_code")
            return None
        return self.get_download_url(pick_code)

    # ==================== 文件夹信息 API ====================

    def get_item_info(self, file_id: str) -> Optional[Dict]:
        """获取文件/文件夹详细信息"""
        params = self._build_api_params({"file_id": file_id})
        result = self.request(self.config.api.GET_FOLDER_INFO_API_URL, 'GET', params=params)
        if result and result.get("state") and isinstance(result.get("data"), dict):
            return result["data"]
        return None

    def get_items_info_batch(self, file_ids: List[str]) -> Dict[str, Dict]:
        """批量获取文件/文件夹详细信息"""
        if not file_ids:
            return {}

        results = {}
        with ThreadPoolExecutor(max_workers=self.config.network.API_CONCURRENT_THREADS) as executor:
            futures = {executor.submit(self.get_item_info, fid): fid for fid in file_ids}
            for future in as_completed(futures):
                fid = futures[future]
                try:
                    info = future.result()
                    if info:
                        results[fid] = info
                except Exception as e:
                    logger.error(f"Error getting info for {fid}: {e}")

        return results

    # ==================== 文件操作 API ====================

    def create_folder(self, parent_id: str, folder_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """创建文件夹，返回 (folder_id, folder_name, error_message)"""
        data = {"pid": parent_id, "file_name": folder_name}
        result = self.request(self.config.api.ADD_FOLDER_API_URL, 'POST', data=data)

        if result and result.get("state") and isinstance(result.get("data"), dict):
            data = result["data"]
            return data.get("file_id"), data.get("file_name"), None

        error = result.get('message', 'Unknown error') if result else "API request failed"
        return None, None, error

    def rename(self, file_id: str, new_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """重命名文件/文件夹，返回 (success, new_name, error_message)"""
        data = {"file_id": file_id, "file_name": new_name}
        result = self.request(self.config.api.UPDATE_FILE_API_URL, 'POST', data=data)

        if result and result.get("state"):
            updated_name = result.get("data", {}).get("file_name", new_name)
            return True, updated_name, None

        error = result.get('message', 'Unknown error') if result else "API request failed"
        return False, None, error

    def move(self, file_ids: List[str], to_cid: str) -> bool:
        """移动文件/文件夹"""
        if not file_ids:
            return False

        data = self._build_api_params({
            "file_ids": ",".join(file_ids),
            "to_cid": to_cid
        })
        result = self.request(self.config.api.MOVE_API_URL, 'POST', data=data)
        return bool(result and result.get("state"))

    def delete(self, file_ids: List[str], parent_id: str = None) -> Tuple[bool, Optional[str]]:
        """删除文件/文件夹，返回 (success, error_message)"""
        if not file_ids:
            return False, "No file IDs provided"

        data = {"file_ids": ",".join(file_ids)}
        if parent_id:
            data["parent_id"] = parent_id

        result = self.request(self.config.api.DELETE_FILE_API_URL, 'POST', data=data)
        if result and result.get("state"):
            return True, None

        error = result.get("message", "Unknown error") if result else "API request failed"
        return False, error

    # ==================== 离线下载 API ====================

    def add_offline_task(self, urls: str, save_path_id: str = '0') -> Tuple[bool, str, Optional[List[Dict]]]:
        """添加离线下载任务"""
        data = {"urls": urls, "wp_path_id": save_path_id}
        result = self.request(self.config.api.CLOUD_DOWNLOAD_API_URL, 'POST', data=data)

        if not (result and result.get("state")):
            error = result.get("message", "Unknown error") if result else "API request failed"
            return False, error, None

        tasks = result.get("data", [])
        failed = [t for t in tasks if not t.get("state")]
        if failed:
            return False, "Some tasks failed", tasks

        return True, "All tasks added successfully", tasks


# ==================== 辅助函数 ====================

def is_folder(item: Dict) -> bool:
    """判断项目是否为文件夹"""
    fc = item.get("fc") or item.get("file_category")
    return fc == "0"


def get_item_attr(item: Dict, *keys: str, default=None) -> Any:
    """从项目中获取属性值（支持多个可能的键名）"""
    for key in keys:
        if key in item:
            return item[key]
    return default
