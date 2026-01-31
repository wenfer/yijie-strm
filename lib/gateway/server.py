"""
STRM 网关 HTTP 服务
提供流媒体重定向、文件列表、STRM 生成等 REST API
"""
from __future__ import annotations
import json
import logging
import os
import threading
import time
from functools import wraps
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional, Callable
from urllib.parse import urlparse, parse_qs, unquote

from ..config import AppConfig, default_config
from ..providers.drive_115 import Client115
from ..services.file_service import FileService
from ..services.strm_service import StrmService
from ..services.drive_service import DriveService
from ..db.factory import create_database

logger = logging.getLogger(__name__)


def is_folder(item: Dict) -> bool:
    """判断项目是否为文件夹"""
    fc = item.get("fc") or item.get("file_category")
    return fc == "0"


def get_item_attr(item: Dict, *keys: str, default=None):
    """从项目中获取属性值（支持多个可能的键名）"""
    for key in keys:
        if key in item:
            return item[key]
    return default


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    # 类级别的服务实例（由 GatewayServer 设置）
    config: AppConfig = None
    drive_service: DriveService = None
    task_service = None
    scheduler_service = None
    server_instance: 'GatewayServer' = None

    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"server.py:{self.__class__.__name__} - {self.address_string()} - {format % args}")

    def _require_auth(self, drive_id: Optional[str] = None) -> bool:
        """检查是否已认证，未认证返回 False 并发送错误响应

        Args:
            drive_id: 可选的网盘 ID，如果不指定则使用当前网盘
        """
        if not self.server_instance:
            logger.error(f"server.py:_require_auth - Server instance not available")
            self._send_error_response("Server not initialized", 500)
            return False

        # 获取目标 drive_id
        target_drive_id = drive_id or self.server_instance._get_current_drive_id()
        if not target_drive_id:
            logger.warning(f"server.py:_require_auth - No drive available")
            self._send_error_response("No drive configured. Please add a drive first.", 401)
            return False

        # 获取服务实例（会验证 token）
        services = self.server_instance.get_services_for_drive(target_drive_id)
        if not services:
            logger.warning(f"server.py:_require_auth - Drive {target_drive_id} not authenticated")
            self._send_error_response("Token 已过期或无效，请重新扫码认证", 401)
            return False

        return True

    def _send_json_response(self, data: Dict, status: int = 200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        if self.config and self.config.gateway.ENABLE_CORS:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_error_response(self, message: str, status: int = 400):
        """发送错误响应"""
        self._send_json_response({"error": message, "status": status}, status)

    def _send_redirect(self, url: str, status: int = 302):
        """发送重定向响应"""
        self.send_response(status)
        self.send_header('Location', url)
        if self.config and self.config.gateway.ENABLE_CORS:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 路由分发
        routes = {
            '/': self._handle_index,
            '/health': self._handle_health,
            '/api/auth/qrcode': self._handle_auth_qrcode,
            '/api/auth/status': self._handle_auth_status,
            '/api/drives': self._handle_drives_list,
            '/api/list': self._handle_list,
            '/api/search': self._handle_search,
            '/api/info': self._handle_info,
            '/api/download': self._handle_download,
            '/api/tasks': self._handle_tasks_list,
            '/api/scheduler/status': self._handle_scheduler_status,
        }

        # 动态路由（带参数）
        if path.startswith('/api/tasks/'):
            self._handle_task_detail(path, query)
            return

        # 流媒体重定向路由
        if path.startswith('/stream/'):
            self._handle_stream(path, query)
            return

        # 静态路由
        handler = routes.get(path)
        if handler:
            handler(query)
        else:
            self._send_error_response("Not Found", 404)

    def do_POST(self):
        """处理 POST 请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error_response("Invalid JSON", 400)
            return

        routes = {
            '/api/auth/exchange': self._handle_auth_exchange,
            '/api/drives': self._handle_drives_add,
            '/api/drives/remove': self._handle_drives_remove,
            '/api/drives/switch': self._handle_drives_switch,
            '/api/drives/update': self._handle_drives_update,
            '/api/tasks': self._handle_tasks_create,
            '/api/scheduler/start': self._handle_scheduler_start,
            '/api/scheduler/stop': self._handle_scheduler_stop,
        }

        # 动态路由（带参数）
        if path.startswith('/api/tasks/'):
            self._handle_task_detail_post(path, data)
            return

        handler = routes.get(path)
        if handler:
            handler(data)
        else:
            self._send_error_response("Not Found", 404)

    # ==================== 路由处理器 ====================

    def _handle_index(self, query: Dict):
        """首页"""
        self._send_json_response({
            "service": "115 STRM Gateway",
            "version": "1.0.0",
            "endpoints": {
                "/health": "健康检查",
                "/stream/{pick_code}": "流媒体重定向",
                "/api/auth/qrcode": "获取认证二维码",
                "/api/auth/status": "检查认证状态",
                "/api/auth/exchange": "交换 Token",
                "/api/drives": "网盘管理",
                "/api/list": "文件列表",
                "/api/search": "文件搜索",
                "/api/info": "文件信息",
                "/api/download": "下载链接",
                "/api/tasks": "任务管理",
                "/api/scheduler/status": "调度器状态",
            }
        })

    def _handle_health(self, query: Dict):
        """健康检查"""
        current_drive_id = self.server_instance._get_current_drive_id() if self.server_instance else None
        is_authenticated = False

        if current_drive_id and self.server_instance:
            services = self.server_instance.get_services_for_drive(current_drive_id)
            is_authenticated = services is not None

        self._send_json_response({
            "status": "ok",
            "timestamp": time.time(),
            "authenticated": is_authenticated,
            "current_drive": current_drive_id
        })

    def _handle_auth_qrcode(self, query: Dict):
        """
        获取认证二维码

        GET /api/auth/qrcode
        """
        from ..providers.drive_115.auth import Auth115
        from ..core.exceptions import AuthenticationError

        auth = Auth115()
        try:
            qrcode_auth = auth.get_qrcode()
            self._send_json_response({
                "success": True,
                "qrcode_url": qrcode_auth.qrcode_url,
                "uid": qrcode_auth.raw_data["uid"],
                "time": qrcode_auth.raw_data["time"],
                "sign": qrcode_auth.raw_data["sign"],
                "code_verifier": qrcode_auth.raw_data["code_verifier"]
            })
        except AuthenticationError as e:
            logger.error(f"server.py:_handle_auth_qrcode - Failed to get QR code: {e}")
            self._send_error_response(f"Failed to get QR code: {e}", 500)

    def _handle_auth_status(self, query: Dict):
        """
        检查认证状态

        GET /api/auth/status?uid=xxx&time=xxx&sign=xxx
        """
        from ..providers.drive_115.auth import Auth115

        uid = query.get('uid', [None])[0]
        time_val = query.get('time', [None])[0]
        sign = query.get('sign', [None])[0]

        if not all([uid, time_val, sign]):
            self._send_error_response("Missing uid, time or sign", 400)
            return

        auth = Auth115()
        status = auth.check_qrcode_status_with_params(uid, time_val, sign)

        status_messages = {
            0: "等待扫描",
            1: "未扫描",
            2: "已扫描"
        }
        self._send_json_response({
            "success": True,
            "status": status,
            "message": status_messages.get(status, "未知状态")
        })

    def _handle_auth_exchange(self, data: Dict):
        """
        交换 Token

        POST /api/auth/exchange
        {
            "uid": "xxx",
            "code_verifier": "xxx",
            "drive_id": "xxx"  // 可选，指定为哪个网盘认证
        }
        """
        from ..providers.drive_115.auth import Auth115

        uid = data.get('uid')
        code_verifier = data.get('code_verifier')
        drive_id = data.get('drive_id')  # 可选参数

        if not uid or not code_verifier:
            self._send_error_response("Missing uid or code_verifier", 400)
            return

        # 如果指定了 drive_id，为该网盘认证
        if drive_id:
            drive = self.drive_service.get_drive(drive_id)
            if not drive:
                self._send_error_response(f"Drive not found: {drive_id}", 404)
                return

            # 使用该网盘的 token 文件路径
            token_file = os.path.expanduser(drive.token_file)
        else:
            # 使用当前网盘或创建新的
            current_drive_id = self.server_instance._get_current_drive_id() if self.server_instance else None
            if current_drive_id:
                drive = self.drive_service.get_drive(current_drive_id)
                token_file = os.path.expanduser(drive.token_file)
                drive_id = current_drive_id
            else:
                self._send_error_response("No drive available. Please add a drive first.", 400)
                return

        auth = Auth115()
        try:
            token = auth.exchange_token(uid, code_verifier=code_verifier)

            # 保存 Token 到文件
            auth.save_token(token, token_file)

            # 清理该网盘的客户端缓存，强制重新创建
            if self.server_instance and drive_id:
                self.server_instance.clear_client_for_drive(drive_id)

            logger.info(f"server.py:_handle_auth_exchange - Authentication successful for drive {drive_id}")
            self._send_json_response({
                "success": True,
                "message": "认证成功",
                "drive_id": drive_id,
                "access_token": token.access_token,
                "expires_in": int(token.expires_at - time.time()) if token.expires_at else 7200
            })
        except Exception as e:
            logger.error(f"server.py:_handle_auth_exchange - Failed to exchange token: {e}")
            self._send_error_response(f"Failed to exchange token: {e}", 500)

    def _handle_drives_list(self, query: Dict):
        """
        获取网盘列表

        GET /api/drives
        """
        drives = self.drive_service.list_drives()
        self._send_json_response({
            "success": True,
            "drives": drives
        })

    def _handle_drives_add(self, data: Dict):
        """
        添加网盘

        POST /api/drives
        {
            "name": "我的115网盘",
            "drive_type": "115"
        }
        """
        name = data.get('name')
        drive_type = data.get('drive_type', '115')

        if not name:
            self._send_error_response("Missing name", 400)
            return

        try:
            drive = self.drive_service.add_drive(name, drive_type)
            logger.info(f"server.py:_handle_drives_add - Drive added: {drive.drive_id}")
            self._send_json_response({
                "success": True,
                "drive": drive.to_dict()
            })
        except Exception as e:
            logger.exception(f"server.py:_handle_drives_add - Failed to add drive: {e}")
            self._send_error_response(str(e), 500)

    def _handle_drives_remove(self, data: Dict):
        """
        删除网盘

        POST /api/drives/remove
        {
            "drive_id": "xxx"
        }
        """
        drive_id = data.get('drive_id')

        if not drive_id:
            self._send_error_response("Missing drive_id", 400)
            return

        # 清理客户端缓存
        if self.server_instance:
            self.server_instance.clear_client_for_drive(drive_id)

        success = self.drive_service.remove_drive(drive_id)
        if success:
            logger.info(f"server.py:_handle_drives_remove - Drive removed: {drive_id}")
            self._send_json_response({
                "success": True,
                "message": "Drive removed successfully"
            })
        else:
            self._send_error_response("Drive not found", 404)

    def _handle_drives_switch(self, data: Dict):
        """
        切换当前网盘

        POST /api/drives/switch
        {
            "drive_id": "xxx"
        }
        """
        drive_id = data.get('drive_id')

        if not drive_id:
            self._send_error_response("Missing drive_id", 400)
            return

        success = self.drive_service.set_current_drive(drive_id)
        if success:
            logger.info(f"server.py:_handle_drives_switch - Switched to drive: {drive_id}")
            self._send_json_response({
                "success": True,
                "message": "Switched to drive successfully"
            })
        else:
            self._send_error_response("Drive not found", 404)

    def _handle_drives_update(self, data: Dict):
        """
        更新网盘信息

        POST /api/drives/update
        {
            "drive_id": "xxx",
            "name": "新名称"
        }
        """
        drive_id = data.get('drive_id')
        name = data.get('name')

        if not drive_id:
            self._send_error_response("Missing drive_id", 400)
            return

        success = self.drive_service.update_drive(drive_id, name)
        if success:
            logger.info(f"server.py:_handle_drives_update - Drive updated: {drive_id}")
            self._send_json_response({
                "success": True,
                "message": "Drive updated successfully"
            })
        else:
            self._send_error_response("Drive not found", 404)

    def _handle_stream(self, path: str, query: Dict):
        """
        流媒体重定向

        GET /stream/{pick_code}?drive_id=xxx
        """
        # 提取 pick_code
        parts = path.split('/')
        if len(parts) < 3:
            self._send_error_response("Invalid pick_code", 400)
            return

        pick_code = parts[2]
        if not pick_code:
            self._send_error_response("Missing pick_code", 400)
            return

        # 获取可选的 drive_id
        drive_id = query.get('drive_id', [None])[0]

        if not self._require_auth(drive_id):
            return

        # 获取服务实例
        target_drive_id = drive_id or self.server_instance._get_current_drive_id()
        services = self.server_instance.get_services_for_drive(target_drive_id)
        if not services:
            self._send_error_response("Failed to get services", 500)
            return

        # 获取下载链接
        strm_service = services["strm_service"]
        url = strm_service.get_stream_url(pick_code)
        if not url:
            logger.error(f"server.py:_handle_stream - Failed to get download URL for {pick_code}")
            self._send_error_response("Failed to get download URL", 500)
            return

        # 重定向到下载链接
        self._send_redirect(url)

    def _handle_list(self, query: Dict):
        """
        文件列表

        GET /api/list?cid=xxx&limit=100&offset=0&drive_id=xxx
        """
        cid = query.get('cid', ['0'])[0]
        limit = int(query.get('limit', ['100'])[0])
        offset = int(query.get('offset', ['0'])[0])
        drive_id = query.get('drive_id', [None])[0]

        if not self._require_auth(drive_id):
            return

        # 获取服务实例
        target_drive_id = drive_id or self.server_instance._get_current_drive_id()
        services = self.server_instance.get_services_for_drive(target_drive_id)
        if not services:
            self._send_error_response("Failed to get services", 500)
            return

        client = services["client"]
        items, total = client.list_files(cid, limit, offset)

        self._send_json_response({
            "cid": cid,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [self._format_item(item) for item in items]
        })

    def _handle_search(self, query: Dict):
        """
        文件搜索

        GET /api/search?keyword=xxx&cid=0&limit=100&drive_id=xxx
        """
        keyword = query.get('keyword', [''])[0]
        if not keyword:
            self._send_error_response("Missing keyword", 400)
            return

        cid = query.get('cid', ['0'])[0]
        limit = int(query.get('limit', ['100'])[0])
        offset = int(query.get('offset', ['0'])[0])
        drive_id = query.get('drive_id', [None])[0]

        if not self._require_auth(drive_id):
            return

        # 获取服务实例
        target_drive_id = drive_id or self.server_instance._get_current_drive_id()
        services = self.server_instance.get_services_for_drive(target_drive_id)
        if not services:
            self._send_error_response("Failed to get services", 500)
            return

        client = services["client"]
        items, total = client.search(keyword, cid, limit, offset)

        self._send_json_response({
            "keyword": keyword,
            "cid": cid,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [self._format_item(item) for item in items]
        })

    def _handle_info(self, query: Dict):
        """
        文件信息

        GET /api/info?file_id=xxx&drive_id=xxx
        GET /api/info?pick_code=xxx&drive_id=xxx
        """
        file_id = query.get('file_id', [None])[0]
        pick_code = query.get('pick_code', [None])[0]
        drive_id = query.get('drive_id', [None])[0]

        if not self._require_auth(drive_id):
            return

        # 获取服务实例
        target_drive_id = drive_id or self.server_instance._get_current_drive_id()
        services = self.server_instance.get_services_for_drive(target_drive_id)
        if not services:
            self._send_error_response("Failed to get services", 500)
            return

        client = services["client"]
        strm_service = services["strm_service"]

        if file_id:
            info = client.get_item_info(file_id)
            if info:
                self._send_json_response({"data": info})
            else:
                self._send_error_response("File not found", 404)
        elif pick_code:
            info = strm_service.get_stream_info(pick_code)
            if info:
                self._send_json_response({"data": info})
            else:
                self._send_error_response("File not found", 404)
        else:
            self._send_error_response("Missing file_id or pick_code", 400)

    def _handle_download(self, query: Dict):
        """
        获取下载链接

        GET /api/download?pick_code=xxx&drive_id=xxx
        """
        pick_code = query.get('pick_code', [None])[0]
        drive_id = query.get('drive_id', [None])[0]

        if not pick_code:
            self._send_error_response("Missing pick_code", 400)
            return

        if not self._require_auth(drive_id):
            return

        # 获取服务实例
        target_drive_id = drive_id or self.server_instance._get_current_drive_id()
        services = self.server_instance.get_services_for_drive(target_drive_id)
        if not services:
            self._send_error_response("Failed to get services", 500)
            return

        strm_service = services["strm_service"]
        url = strm_service.get_stream_url(pick_code)
        if url:
            self._send_json_response({"pick_code": pick_code, "url": url})
        else:
            logger.error(f"server.py:_handle_download - Failed to get download URL for {pick_code}")
            self._send_error_response("Failed to get download URL", 500)

    def _format_item(self, item: Dict) -> Dict:
        """格式化文件项"""
        return {
            "id": get_item_attr(item, "fid", "file_id"),
            "name": get_item_attr(item, "fn", "file_name"),
            "size": get_item_attr(item, "fs", "file_size"),
            "pick_code": get_item_attr(item, "pc", "pick_code"),
            "is_folder": is_folder(item),
            "parent_id": get_item_attr(item, "pid", "parent_id"),
        }

    # ==================== 任务管理 API ====================

    def _handle_tasks_list(self, query: Dict):
        """
        获取任务列表

        GET /api/tasks?drive_id=xxx
        """
        if not self.task_service:
            self._send_error_response("Task service not available", 503)
            return

        drive_id = query.get('drive_id', [None])[0]

        try:
            tasks = self.task_service.list_tasks(drive_id)
            self._send_json_response({
                "success": True,
                "tasks": [task.to_dict() for task in tasks]
            })
        except Exception as e:
            logger.exception(f"server.py:_handle_tasks_list - Failed to list tasks: {e}")
            self._send_error_response(str(e), 500)

    def _handle_tasks_create(self, data: Dict):
        """
        创建任务

        POST /api/tasks
        """
        if not self.task_service:
            self._send_error_response("Task service not available", 503)
            return

        required_fields = ['task_name', 'drive_id', 'source_cid', 'output_dir']
        for field in required_fields:
            if not data.get(field):
                self._send_error_response(f"Missing {field}", 400)
                return

        try:
            task = self.task_service.create_task(data)

            # 如果启用了调度，添加到调度器
            if task.schedule_enabled and self.scheduler_service:
                self.scheduler_service.schedule_task(task)

            logger.info(f"server.py:_handle_tasks_create - Task created: {task.task_id}")
            self._send_json_response({
                "success": True,
                "task": task.to_dict()
            })
        except Exception as e:
            logger.exception(f"server.py:_handle_tasks_create - Failed to create task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_detail(self, path: str, query: Dict):
        """
        处理任务详情相关的 GET 请求

        GET /api/tasks/{task_id}
        GET /api/tasks/{task_id}/status
        GET /api/tasks/{task_id}/statistics
        GET /api/tasks/{task_id}/logs
        GET /api/tasks/{task_id}/records
        """
        if not self.task_service:
            self._send_error_response("Task service not available", 503)
            return

        parts = path.split('/')
        if len(parts) < 4:
            self._send_error_response("Invalid task path", 400)
            return

        task_id = parts[3]

        # 子路由
        if len(parts) == 4:
            # GET /api/tasks/{task_id}
            self._handle_task_get(task_id)
        elif len(parts) == 5:
            action = parts[4]
            if action == 'status':
                self._handle_task_status(task_id)
            elif action == 'statistics':
                self._handle_task_statistics(task_id)
            elif action == 'logs':
                limit = int(query.get('limit', ['50'])[0])
                self._handle_task_logs(task_id, limit)
            elif action == 'records':
                self._handle_task_records(task_id)
            else:
                self._send_error_response("Unknown action", 404)
        else:
            self._send_error_response("Invalid task path", 400)

    def _handle_task_detail_post(self, path: str, data: Dict):
        """
        处理任务详情相关的 POST 请求

        PUT /api/tasks/{task_id}
        DELETE /api/tasks/{task_id}
        POST /api/tasks/{task_id}/execute
        """
        if not self.task_service:
            self._send_error_response("Task service not available", 503)
            return

        parts = path.split('/')
        if len(parts) < 4:
            self._send_error_response("Invalid task path", 400)
            return

        task_id = parts[3]

        # 子路由
        if len(parts) == 4:
            # PUT /api/tasks/{task_id} - 更新任务
            self._handle_task_update(task_id, data)
        elif len(parts) == 5:
            action = parts[4]
            if action == 'execute':
                # POST /api/tasks/{task_id}/execute
                self._handle_task_execute(task_id, data)
            elif action == 'delete':
                # POST /api/tasks/{task_id}/delete
                self._handle_task_delete(task_id)
            else:
                self._send_error_response("Unknown action", 404)
        else:
            self._send_error_response("Invalid task path", 400)

    def _handle_task_get(self, task_id: str):
        """获取任务详情"""
        try:
            task = self.task_service.get_task(task_id)
            if task:
                self._send_json_response({
                    "success": True,
                    "task": task.to_dict()
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"server.py:_handle_task_get - Failed to get task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_update(self, task_id: str, data: Dict):
        """更新任务"""
        try:
            success = self.task_service.update_task(task_id, data)
            if success:
                # 如果调度配置改变，重新调度
                if any(k in data for k in ['schedule_enabled', 'schedule_type', 'schedule_config']):
                    task = self.task_service.get_task(task_id)
                    if task and self.scheduler_service:
                        self.scheduler_service.reschedule_task(task)

                logger.info(f"server.py:_handle_task_update - Task updated: {task_id}")
                self._send_json_response({
                    "success": True,
                    "message": "Task updated successfully"
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"server.py:_handle_task_update - Failed to update task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_delete(self, task_id: str):
        """删除任务"""
        try:
            # 取消调度
            if self.scheduler_service:
                self.scheduler_service.unschedule_task(task_id)

            success = self.task_service.delete_task(task_id)
            if success:
                logger.info(f"server.py:_handle_task_delete - Task deleted: {task_id}")
                self._send_json_response({
                    "success": True,
                    "message": "Task deleted successfully"
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"server.py:_handle_task_delete - Failed to delete task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_execute(self, task_id: str, data: Dict):
        """手动执行任务"""
        if not self.scheduler_service:
            self._send_error_response("Scheduler service not available", 503)
            return

        try:
            force = data.get('force', False)
            success = self.scheduler_service.run_task_now(task_id)

            if success:
                logger.info(f"server.py:_handle_task_execute - Task execution started: {task_id}")
                self._send_json_response({
                    "success": True,
                    "message": "Task execution started"
                })
            else:
                self._send_error_response("Task is already running", 409)
        except Exception as e:
            logger.exception(f"server.py:_handle_task_execute - Failed to execute task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_status(self, task_id: str):
        """获取任务状态"""
        try:
            task = self.task_service.get_task(task_id)
            if task:
                self._send_json_response({
                    "success": True,
                    "status": task.status,
                    "last_run_time": task.last_run_time,
                    "last_run_status": task.last_run_status,
                    "last_run_message": task.last_run_message,
                    "next_run_time": task.next_run_time
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"server.py:_handle_task_status - Failed to get task status: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_statistics(self, task_id: str):
        """获取任务统计"""
        try:
            stats = self.task_service.get_task_statistics(task_id)
            if stats:
                self._send_json_response({
                    "success": True,
                    "statistics": stats
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"server.py:_handle_task_statistics - Failed to get task statistics: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_logs(self, task_id: str, limit: int = 50):
        """获取任务日志"""
        try:
            logs = self.task_service.get_task_logs(task_id, limit)
            self._send_json_response({
                "success": True,
                "logs": logs
            })
        except Exception as e:
            logger.exception(f"server.py:_handle_task_logs - Failed to get task logs: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_records(self, task_id: str):
        """获取任务的 STRM 记录"""
        try:
            records = self.task_service.get_strm_records(task_id)
            self._send_json_response({
                "success": True,
                "records": records
            })
        except Exception as e:
            logger.exception(f"server.py:_handle_task_records - Failed to get task records: {e}")
            self._send_error_response(str(e), 500)

    # ==================== 调度器管理 API ====================

    def _handle_scheduler_status(self, query: Dict):
        """
        获取调度器状态

        GET /api/scheduler/status
        """
        if not self.scheduler_service:
            self._send_error_response("Scheduler service not available", 503)
            return

        try:
            status = self.scheduler_service.get_scheduler_status()
            self._send_json_response({
                "success": True,
                "scheduler": status
            })
        except Exception as e:
            logger.exception(f"server.py:_handle_scheduler_status - Failed to get scheduler status: {e}")
            self._send_error_response(str(e), 500)

    def _handle_scheduler_start(self, data: Dict):
        """
        启动调度器

        POST /api/scheduler/start
        """
        if not self.scheduler_service:
            self._send_error_response("Scheduler service not available", 503)
            return

        try:
            success = self.scheduler_service.start()
            if success:
                logger.info(f"server.py:_handle_scheduler_start - Scheduler started")
                self._send_json_response({
                    "success": True,
                    "message": "Scheduler started"
                })
            else:
                self._send_error_response("Scheduler already running", 409)
        except Exception as e:
            logger.exception(f"server.py:_handle_scheduler_start - Failed to start scheduler: {e}")
            self._send_error_response(str(e), 500)

    def _handle_scheduler_stop(self, data: Dict):
        """
        停止调度器

        POST /api/scheduler/stop
        """
        if not self.scheduler_service:
            self._send_error_response("Scheduler service not available", 503)
            return

        try:
            success = self.scheduler_service.stop()
            if success:
                logger.info(f"server.py:_handle_scheduler_stop - Scheduler stopped")
                self._send_json_response({
                    "success": True,
                    "message": "Scheduler stopped"
                })
            else:
                self._send_error_response("Scheduler not running", 409)
        except Exception as e:
            logger.exception(f"server.py:_handle_scheduler_stop - Failed to stop scheduler: {e}")
            self._send_error_response(str(e), 500)


class GatewayServer:
    """STRM 网关服务器"""

    def __init__(self, config: AppConfig = None):
        self.config = config or default_config
        self.drive_service: DriveService = DriveService(self.config)
        self.task_service = None
        self.scheduler_service = None
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._db = None

        # 客户端池：缓存每个 drive 的服务实例
        self._client_pool: Dict[str, Dict] = {}
        self._client_pool_lock = threading.Lock()

        # 初始化数据库和任务服务
        self._initialize_task_services()

    def _initialize_task_services(self):
        """初始化任务管理服务"""
        try:
            # 创建数据库连接
            self._db = create_database(self.config)
            self._db.connect()

            # 创建任务服务
            from ..services.task_service import TaskService
            self.task_service = TaskService(self._db)

            # 创建调度器服务（不需要全局 strm_service）
            from ..services.scheduler_service import SchedulerService
            self.scheduler_service = SchedulerService(
                self.task_service,
                drive_service=self.drive_service,
                config=self.config
            )

            logger.info("server.py:_initialize_task_services - Task services initialized")
        except Exception as e:
            logger.error(f"server.py:_initialize_task_services - Failed to initialize task services: {e}")
            # 任务服务初始化失败不影响网关启动

    def _get_current_drive_id(self) -> Optional[str]:
        """获取当前网盘 ID"""
        try:
            current_drive = self.drive_service.get_current_drive()
            return current_drive.drive_id if current_drive else None
        except Exception as e:
            logger.error(f"server.py:_get_current_drive_id - Failed to get current drive: {e}")
            return None

    def get_services_for_drive(self, drive_id: str) -> Optional[Dict]:
        """
        获取指定网盘的服务实例（带缓存）

        Args:
            drive_id: 网盘 ID

        Returns:
            {
                "client": Client115,
                "file_service": FileService,
                "strm_service": StrmService
            }
            如果 token 无效或网盘不存在，返回 None
        """
        with self._client_pool_lock:
            # 检查缓存
            if drive_id in self._client_pool:
                cached = self._client_pool[drive_id]
                # 验证 token 是否仍然有效
                try:
                    client = cached["client"]
                    if client.token_watcher and client.token_watcher.is_token_valid():
                        logger.debug(f"server.py:get_services_for_drive - Using cached services for drive {drive_id}")
                        return cached
                    else:
                        # Token 已过期，清理缓存
                        logger.info(f"server.py:get_services_for_drive - Token expired for drive {drive_id}, clearing cache")
                        client.close()
                        del self._client_pool[drive_id]
                except Exception as e:
                    logger.warning(f"server.py:get_services_for_drive - Error checking token validity: {e}")
                    # 清理缓存
                    if drive_id in self._client_pool:
                        try:
                            self._client_pool[drive_id]["client"].close()
                        except:
                            pass
                        del self._client_pool[drive_id]

            # 创建新的服务实例
            try:
                logger.info(f"server.py:get_services_for_drive - Creating new services for drive {drive_id}")
                client = self.drive_service.get_client(drive_id)
                if not client:
                    logger.error(f"server.py:get_services_for_drive - Failed to get client for drive {drive_id}")
                    return None

                file_service = FileService(client, self.config)
                strm_service = StrmService(file_service, self.config, self.task_service, self.drive_service)

                # 缓存起来
                services = {
                    "client": client,
                    "file_service": file_service,
                    "strm_service": strm_service
                }
                self._client_pool[drive_id] = services
                logger.info(f"server.py:get_services_for_drive - Services created and cached for drive {drive_id}")
                return services
            except Exception as e:
                logger.exception(f"server.py:get_services_for_drive - Failed to create services for drive {drive_id}: {e}")
                return None

    def clear_client_for_drive(self, drive_id: str):
        """清理指定网盘的客户端缓存"""
        with self._client_pool_lock:
            if drive_id in self._client_pool:
                try:
                    self._client_pool[drive_id]["client"].close()
                except Exception as e:
                    logger.warning(f"server.py:clear_client_for_drive - Error closing client: {e}")
                del self._client_pool[drive_id]
                logger.info(f"server.py:clear_client_for_drive - Cleared cache for drive {drive_id}")

    def clear_client_pool(self):
        """清空整个客户端池"""
        with self._client_pool_lock:
            for drive_id, services in self._client_pool.items():
                try:
                    services["client"].close()
                except Exception as e:
                    logger.warning(f"server.py:clear_client_pool - Error closing client for {drive_id}: {e}")
            self._client_pool.clear()
            logger.info("server.py:clear_client_pool - Client pool cleared")

    def start(self, blocking: bool = True):
        """
        启动网关服务

        Args:
            blocking: 是否阻塞运行
        """
        logger.info("server.py:start - Starting gateway server...")

        # 设置处理器的配置
        GatewayHandler.config = self.config
        GatewayHandler.drive_service = self.drive_service
        GatewayHandler.task_service = self.task_service
        GatewayHandler.scheduler_service = self.scheduler_service
        GatewayHandler.server_instance = self

        # 创建 HTTP 服务器
        server_address = (self.config.gateway.HOST, self.config.gateway.PORT)
        self._server = HTTPServer(server_address, GatewayHandler)

        logger.info(f"server.py:start - STRM Gateway started on http://{self.config.gateway.HOST}:{self.config.gateway.PORT}")

        if blocking:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                logger.info("server.py:start - Shutting down...")
                self.stop()
        else:
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()

    def stop(self):
        """停止网关服务"""
        logger.info("server.py:stop - Stopping gateway server...")

        # 停止调度器
        if self.scheduler_service:
            self.scheduler_service.stop()
            self.scheduler_service = None

        # 清空客户端池
        self.clear_client_pool()

        if self._server:
            self._server.shutdown()
            self._server = None

        # 关闭数据库连接
        if self._db:
            self._db.close()
            self._db = None

        logger.info("server.py:stop - Gateway server stopped")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def run_gateway(host: str = "0.0.0.0", port: int = 8115, debug: bool = False):
    """
    运行 STRM 网关服务

    Args:
        host: 监听地址
        port: 监听端口
        debug: 调试模式
    """
    config = AppConfig.from_env()
    config.gateway.HOST = host
    config.gateway.PORT = port
    config.gateway.DEBUG = debug

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )

    server = GatewayServer(config)
    server.start(blocking=True)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='115 STRM Gateway Server')
    parser.add_argument('--host', default='0.0.0.0', help='Listen host')
    parser.add_argument('--port', type=int, default=8115, help='Listen port')
    parser.add_argument('--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()
    run_gateway(args.host, args.port, args.debug)

