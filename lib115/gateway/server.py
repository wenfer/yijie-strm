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

logger = logging.getLogger(__name__)


class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    # 类级别的服务实例（由 GatewayServer 设置）
    config: AppConfig = None
    client: Client115 = None
    file_service: FileService = None
    strm_service: StrmService = None

    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.address_string()} - {format % args}")

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
            '/api/list': self._handle_list,
            '/api/search': self._handle_search,
            '/api/info': self._handle_info,
            '/api/download': self._handle_download,
            '/api/strm/generate': self._handle_strm_generate,
            '/api/strm/index': self._handle_strm_index,
        }

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
            '/api/strm/generate': self._handle_strm_generate_post,
            '/api/strm/sync': self._handle_strm_sync,
        }

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
                "/api/list": "文件列表",
                "/api/search": "文件搜索",
                "/api/info": "文件信息",
                "/api/download": "下载链接",
                "/api/strm/generate": "生成 STRM 文件",
                "/api/strm/index": "索引统计",
            }
        })

    def _handle_health(self, query: Dict):
        """健康检查"""
        self._send_json_response({
            "status": "ok",
            "timestamp": time.time(),
            "token_valid": self.client.token_watcher.is_token_valid() if self.client else False
        })

    def _handle_stream(self, path: str, query: Dict):
        """
        流媒体重定向

        GET /stream/{pick_code}
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
        pick_code = query.get('pick_code', [None])[0]
        if not pick_code:
            self._send_error_response("Missing pick_code", 400)
            return

        url = self.strm_service.get_stream_url(pick_code)
        if url:
            self._send_json_response({"pick_code": pick_code, "url": url})
        else:
            self._send_error_response("Failed to get download URL", 500)

    def _handle_strm_generate(self, query: Dict):
        """
        生成 STRM 文件（GET 方式，简单参数）

        GET /api/strm/generate?cid=xxx&output=/path/to/output
        """
        cid = query.get('cid', [None])[0]
        output = query.get('output', [None])[0]

        if not cid or not output:
            self._send_error_response("Missing cid or output", 400)
            return

        base_url = query.get('base_url', [''])[0]
        if not base_url and self.config:
            base_url = self.config.gateway.STRM_BASE_URL

        try:
            strm_files = self.strm_service.generate_strm_files(
                root_cid=cid,
                output_dir=output,
                base_url=base_url
            )
            self._send_json_response({
                "success": True,
                "count": len(strm_files),
                "output_dir": output
            })
        except Exception as e:
            logger.exception(f"STRM generation failed: {e}")
            self._send_error_response(str(e), 500)

    def _handle_strm_generate_post(self, data: Dict):
        """
        生成 STRM 文件（POST 方式，完整参数）

        POST /api/strm/generate
        {
            "cid": "xxx",
            "output_dir": "/path/to/output",
            "base_url": "http://localhost:8115",
            "include_audio": false,
            "preserve_structure": true
        }
        """
        cid = data.get('cid')
        output_dir = data.get('output_dir')

        if not cid or not output_dir:
            self._send_error_response("Missing cid or output_dir", 400)
            return

        base_url = data.get('base_url', '')
        if not base_url and self.config:
            base_url = self.config.gateway.STRM_BASE_URL

        try:
            strm_files = self.strm_service.generate_strm_files(
                root_cid=cid,
                output_dir=output_dir,
                base_url=base_url,
                include_audio=data.get('include_audio', False),
                preserve_structure=data.get('preserve_structure', True)
            )
            self._send_json_response({
                "success": True,
                "count": len(strm_files),
                "output_dir": output_dir
            })
        except Exception as e:
            logger.exception(f"STRM generation failed: {e}")
            self._send_error_response(str(e), 500)

    def _handle_strm_sync(self, data: Dict):
        """
        同步 STRM 文件

        POST /api/strm/sync
        {
            "cid": "xxx",
            "strm_dir": "/path/to/strm",
            "base_url": "http://localhost:8115",
            "delete_orphans": false
        }
        """
        from ..services.strm_service import StrmGenerator

        cid = data.get('cid')
        strm_dir = data.get('strm_dir')

        if not cid or not strm_dir:
            self._send_error_response("Missing cid or strm_dir", 400)
            return

        base_url = data.get('base_url', '')
        if not base_url and self.config:
            base_url = self.config.gateway.STRM_BASE_URL

        try:
            generator = StrmGenerator(self.strm_service)
            added, updated, deleted = generator.sync_strm_files(
                root_cid=cid,
                strm_dir=strm_dir,
                base_url=base_url,
                delete_orphans=data.get('delete_orphans', False)
            )
            self._send_json_response({
                "success": True,
                "added": added,
                "updated": updated,
                "deleted": deleted
            })
        except Exception as e:
            logger.exception(f"STRM sync failed: {e}")
            self._send_error_response(str(e), 500)

    def _handle_strm_index(self, query: Dict):
        """
        获取索引统计

        GET /api/strm/index
        """
        stats = self.strm_service.get_index_stats()
        self._send_json_response(stats)

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


class GatewayServer:
    """STRM 网关服务器"""

    def __init__(self, config: AppConfig = None):
        self.config = config or default_config
        self.client: Optional[Client115] = None
        self.file_service: Optional[FileService] = None
        self.strm_service: Optional[StrmService] = None
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = True):
        """
        启动网关服务

        Args:
            blocking: 是否阻塞运行
        """
        # 初始化服务
        logger.info("Initializing 115 client...")
        self.client = Client115(self.config)
        self.file_service = FileService(self.client, self.config)
        self.strm_service = StrmService(self.file_service, self.config)

        # 设置处理器的服务实例
        GatewayHandler.config = self.config
        GatewayHandler.client = self.client
        GatewayHandler.file_service = self.file_service
        GatewayHandler.strm_service = self.strm_service

        # 创建 HTTP 服务器
        server_address = (self.config.gateway.HOST, self.config.gateway.PORT)
        self._server = HTTPServer(server_address, GatewayHandler)

        logger.info(f"STRM Gateway starting on http://{self.config.gateway.HOST}:{self.config.gateway.PORT}")

        if blocking:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                self.stop()
        else:
            self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._server_thread.start()

    def stop(self):
        """停止网关服务"""
        if self._server:
            self._server.shutdown()
            self._server = None

        if self.client:
            self.client.close()
            self.client = None

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
