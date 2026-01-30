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
from ..api.client import Client115, is_folder, get_item_attr
from ..services.file_service import FileService
from ..services.strm_service import StrmService
from ..services.drive_service import DriveService
from ..services.task_service import TaskService
from ..services.scheduler_service import SchedulerService
from ..db.factory import create_database

logger = logging.getLogger(__name__)


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    # 类级别的服务实例（由 GatewayServer 设置）
    config: AppConfig = None
    client: Client115 = None
    file_service: FileService = None
    strm_service: StrmService = None
    drive_service: DriveService = None
    task_service: TaskService = None
    scheduler_service: SchedulerService = None
    server_instance: 'GatewayServer' = None

    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.address_string()} - {format % args}")

    def _require_auth(self) -> bool:
        """检查是否已认证，未认证返回 False 并发送错误响应"""
        if not self.client or not self.client.token_watcher.is_token_valid():
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
        is_authenticated = self.client and self.client.token_watcher.is_token_valid()
        self._send_json_response({
            "status": "ok",
            "timestamp": time.time(),
            "authenticated": is_authenticated,
            "token_valid": is_authenticated
        })

    def _handle_auth_qrcode(self, query: Dict):
        """
        获取认证二维码

        GET /api/auth/qrcode
        """
        from ..auth.token_manager import TokenManager

        token_manager = TokenManager(self.config)
        qrcode_info = token_manager.get_qrcode_for_auth()

        if qrcode_info:
            self._send_json_response({
                "success": True,
                "qrcode_url": qrcode_info["qrcode_url"],
                "uid": qrcode_info["uid"],
                "time": qrcode_info["time"],
                "sign": qrcode_info["sign"],
                "code_verifier": qrcode_info["code_verifier"]
            })
        else:
            self._send_error_response("Failed to get QR code", 500)

    def _handle_auth_status(self, query: Dict):
        """
        检查认证状态

        GET /api/auth/status?uid=xxx&time=xxx&sign=xxx
        """
        from ..auth.token_manager import TokenManager

        uid = query.get('uid', [None])[0]
        time_val = query.get('time', [None])[0]
        sign = query.get('sign', [None])[0]

        if not all([uid, time_val, sign]):
            self._send_error_response("Missing uid, time or sign", 400)
            return

        token_manager = TokenManager(self.config)
        status_data = token_manager.check_qrcode_status(uid, time_val, sign)

        if status_data:
            self._send_json_response({
                "success": True,
                "status": status_data.get("data", {}).get("status", 1),
                "message": "已扫描" if status_data.get("data", {}).get("status") == 2 else "等待扫描"
            })
        else:
            self._send_error_response("Failed to check status", 500)

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
        from ..auth.token_manager import TokenManager

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
            config = self.config.__class__.from_env()
            config.auth.TOKEN_FILE_PATH = os.path.expanduser(drive.token_file)
            token_manager = TokenManager(config)
        else:
            # 使用默认配置
            token_manager = TokenManager(self.config)

        token_info = token_manager.exchange_token_with_device_code(uid, code_verifier)

        if token_info:
            # 如果是为特定网盘认证，切换到该网盘
            if drive_id and self.server_instance:
                success = self.server_instance.initialize_client_for_drive(drive_id)
                if not success:
                    self._send_error_response("Failed to initialize client for drive", 500)
                    return
            # 否则初始化默认客户端
            elif self.server_instance:
                success = self.server_instance.initialize_client()
                if not success:
                    self._send_error_response("Failed to initialize client", 500)
                    return

            self._send_json_response({
                "success": True,
                "message": "认证成功",
                "access_token": token_info.get("access_token"),
                "expires_in": token_info.get("expires_in")
            })
        else:
            self._send_error_response("Failed to exchange token", 500)

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
            self._send_json_response({
                "success": True,
                "drive": drive.to_dict()
            })
        except Exception as e:
            logger.exception(f"Failed to add drive: {e}")
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

        success = self.drive_service.remove_drive(drive_id)
        if success:
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
            # 重新初始化客户端以使用新的网盘
            if self.server_instance:
                self.server_instance.initialize_client_for_drive(drive_id)

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
            self._send_json_response({
                "success": True,
                "message": "Drive updated successfully"
            })
        else:
            self._send_error_response("Drive not found", 404)

    def _handle_stream(self, path: str, query: Dict):
        """
        流媒体重定向

        GET /stream/{pick_code}
        """
        if not self._require_auth():
            return

        # 提取 pick_code
        parts = path.split('/')
        if len(parts) < 3:
            self._send_error_response("Invalid pick_code", 400)
            return

        pick_code = parts[2]
        if not pick_code:
            self._send_error_response("Missing pick_code", 400)
            return

        # 获取下载链接
        url = self.strm_service.get_stream_url(pick_code)
        if not url:
            self._send_error_response("Failed to get download URL", 500)
            return

        # 重定向到下载链接
        self._send_redirect(url)

    def _handle_list(self, query: Dict):
        """
        文件列表

        GET /api/list?cid=xxx&limit=100&offset=0
        """
        if not self._require_auth():
            return

        cid = query.get('cid', ['0'])[0]
        limit = int(query.get('limit', ['100'])[0])
        offset = int(query.get('offset', ['0'])[0])

        items, total = self.client.list_files(cid, limit, offset)

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

        GET /api/search?keyword=xxx&cid=0&limit=100
        """
        if not self._require_auth():
            return

        keyword = query.get('keyword', [''])[0]
        if not keyword:
            self._send_error_response("Missing keyword", 400)
            return

        cid = query.get('cid', ['0'])[0]
        limit = int(query.get('limit', ['100'])[0])
        offset = int(query.get('offset', ['0'])[0])

        items, total = self.client.search(keyword, cid, limit, offset)

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

        GET /api/info?file_id=xxx
        GET /api/info?pick_code=xxx
        """
        if not self._require_auth():
            return

        file_id = query.get('file_id', [None])[0]
        pick_code = query.get('pick_code', [None])[0]

        if file_id:
            info = self.client.get_item_info(file_id)
            if info:
                self._send_json_response({"data": info})
            else:
                self._send_error_response("File not found", 404)
        elif pick_code:
            info = self.strm_service.get_stream_info(pick_code)
            if info:
                self._send_json_response({"data": info})
            else:
                self._send_error_response("File not found", 404)
        else:
            self._send_error_response("Missing file_id or pick_code", 400)

    def _handle_download(self, query: Dict):
        """
        获取下载链接

        GET /api/download?pick_code=xxx
        """
        if not self._require_auth():
            return

        pick_code = query.get('pick_code', [None])[0]
        if not pick_code:
            self._send_error_response("Missing pick_code", 400)
            return

        url = self.strm_service.get_stream_url(pick_code)
        if url:
            self._send_json_response({"pick_code": pick_code, "url": url})
        else:
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
            logger.exception(f"Failed to list tasks: {e}")
            self._send_error_response(str(e), 500)

    def _handle_tasks_create(self, data: Dict):
        """
        创建任务

        POST /api/tasks
        {
            "task_name": "我的任务",
            "drive_id": "xxx",
            "source_cid": "xxx",
            "output_dir": "/path/to/output",
            "base_url": "http://localhost:8115",
            "include_video": true,
            "include_audio": false,
            "custom_extensions": [".mp4", ".mkv"],
            "schedule_enabled": false,
            "schedule_type": "interval",
            "schedule_config": {"interval": 3600, "unit": "seconds"},
            "watch_enabled": false,
            "watch_interval": 3600,
            "delete_orphans": true,
            "preserve_structure": true
        }
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

            self._send_json_response({
                "success": True,
                "task": task.to_dict()
            })
        except Exception as e:
            logger.exception(f"Failed to create task: {e}")
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
            logger.exception(f"Failed to get task: {e}")
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

                self._send_json_response({
                    "success": True,
                    "message": "Task updated successfully"
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"Failed to update task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_delete(self, task_id: str):
        """删除任务"""
        try:
            # 取消调度
            if self.scheduler_service:
                self.scheduler_service.unschedule_task(task_id)

            success = self.task_service.delete_task(task_id)
            if success:
                self._send_json_response({
                    "success": True,
                    "message": "Task deleted successfully"
                })
            else:
                self._send_error_response("Task not found", 404)
        except Exception as e:
            logger.exception(f"Failed to delete task: {e}")
            self._send_error_response(str(e), 500)

    def _handle_task_execute(self, task_id: str, data: Dict):
        """手动执行任务"""
        # 不使用 _require_auth，因为任务可能使用不同的 drive
        # 让任务执行时自己检查 token 有效性

        if not self.scheduler_service:
            self._send_error_response("Scheduler service not available", 503)
            return

        try:
            force = data.get('force', False)
            success = self.scheduler_service.run_task_now(task_id)

            if success:
                self._send_json_response({
                    "success": True,
                    "message": "Task execution started"
                })
            else:
                self._send_error_response("Task is already running", 409)
        except Exception as e:
            logger.exception(f"Failed to execute task: {e}")
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
            logger.exception(f"Failed to get task status: {e}")
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
            logger.exception(f"Failed to get task statistics: {e}")
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
            logger.exception(f"Failed to get task logs: {e}")
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
            logger.exception(f"Failed to get task records: {e}")
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
            logger.exception(f"Failed to get scheduler status: {e}")
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
                self._send_json_response({
                    "success": True,
                    "message": "Scheduler started"
                })
            else:
                self._send_error_response("Scheduler already running", 409)
        except Exception as e:
            logger.exception(f"Failed to start scheduler: {e}")
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
                self._send_json_response({
                    "success": True,
                    "message": "Scheduler stopped"
                })
            else:
                self._send_error_response("Scheduler not running", 409)
        except Exception as e:
            logger.exception(f"Failed to stop scheduler: {e}")
            self._send_error_response(str(e), 500)


class GatewayServer:
    """STRM 网关服务器"""

    def __init__(self, config: AppConfig = None):
        self.config = config or default_config
        self.client: Optional[Client115] = None
        self.file_service: Optional[FileService] = None
        self.strm_service: Optional[StrmService] = None
        self.drive_service: DriveService = DriveService(self.config)
        self.task_service: Optional[TaskService] = None
        self.scheduler_service: Optional[SchedulerService] = None
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._db = None

        # 初始化数据库和任务服务
        self._initialize_task_services()

    def _initialize_task_services(self):
        """初始化任务管理服务"""
        try:
            # 创建数据库连接
            self._db = create_database(self.config)
            self._db.connect()

            # 创建任务服务
            self.task_service = TaskService(self._db)

            # 创建调度器服务（不需要 strm_service）
            self.scheduler_service = SchedulerService(self.task_service, strm_service=None)

            logger.info("Task services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize task services: {e}")
            # 任务服务初始化失败不影响网关启动

    def start(self, blocking: bool = True):
        """
        启动网关服务

        Args:
            blocking: 是否阻塞运行
        """
        # 不在启动时初始化客户端，等待用户认证后再初始化
        logger.info("Starting gateway server...")

        # 设置处理器的配置
        GatewayHandler.config = self.config
        GatewayHandler.client = None
        GatewayHandler.file_service = None
        GatewayHandler.strm_service = None
        GatewayHandler.drive_service = self.drive_service
        GatewayHandler.task_service = self.task_service
        GatewayHandler.scheduler_service = self.scheduler_service
        GatewayHandler.server_instance = self

        # 创建 HTTP 服务器
        server_address = (self.config.gateway.HOST, self.config.gateway.PORT)
        self._server = HTTPServer(server_address, GatewayHandler)

        logger.info(f"STRM Gateway started on http://{self.config.gateway.HOST}:{self.config.gateway.PORT}")

        if blocking:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                self.stop()
        else:
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()

    def initialize_client(self):
        """初始化 115 客户端（认证成功后调用）"""
        try:
            logger.info("Initializing 115 client...")
            self.client = Client115(self.config, auto_start_watcher=True)
            self.file_service = FileService(self.client, self.config)
            self.strm_service = StrmService(self.file_service, self.config, self.task_service, self.drive_service)

            # 更新处理器的服务实例
            GatewayHandler.client = self.client
            GatewayHandler.file_service = self.file_service
            GatewayHandler.strm_service = self.strm_service

            # 更新调度器服务的 strm_service 并启动
            if self.scheduler_service:
                self.scheduler_service.set_strm_service(self.strm_service)
                if not self.scheduler_service.is_running():
                    self.scheduler_service.start()
                    logger.info("Scheduler service started")

            logger.info("115 client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            return False

    def initialize_client_for_drive(self, drive_id: str):
        """为指定网盘初始化客户端"""
        try:
            # 关闭现有客户端
            if self.client:
                self.client.close()
                self.client = None

            drive = self.drive_service.get_drive(drive_id)
            if not drive:
                logger.error(f"Drive not found: {drive_id}")
                return False

            # 创建临时配置，使用该网盘的 token 文件
            config = AppConfig.from_env()
            config.auth.TOKEN_FILE_PATH = os.path.expanduser(drive.token_file)

            logger.info(f"Initializing client for drive: {drive_id} ({drive.name})")
            self.client = Client115(config, auto_start_watcher=True)
            self.file_service = FileService(self.client, config)
            self.strm_service = StrmService(self.file_service, config, self.task_service, self.drive_service)

            # 更新处理器的服务实例
            GatewayHandler.client = self.client
            GatewayHandler.file_service = self.file_service
            GatewayHandler.strm_service = self.strm_service

            # 更新调度器服务的 strm_service 并重启
            if self.scheduler_service:
                self.scheduler_service.stop()
                self.scheduler_service.set_strm_service(self.strm_service)
                self.scheduler_service.start()
                logger.info("Scheduler service restarted for new drive")

            logger.info(f"Client initialized for drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize client for drive {drive_id}: {e}")
            return False

    def stop(self):
        """停止网关服务"""
        # 停止调度器
        if self.scheduler_service:
            self.scheduler_service.stop()
            self.scheduler_service = None

        if self._server:
            self._server.shutdown()
            self._server = None

        if self.client:
            self.client.close()
            self.client = None

        # 关闭数据库连接
        if self._db:
            self._db.close()
            self._db = None

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
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

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
