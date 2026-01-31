#!/usr/bin/env python3
"""
多网盘 STRM 网关服务启动脚本

使用方法:
    python run_gateway.py                    # 默认配置启动
    python run_gateway.py --port 8080        # 指定端口
    python run_gateway.py --debug            # 调试模式

环境变量:
    GATEWAY_HOST: 监听地址 (默认: 0.0.0.0)
    GATEWAY_PORT: 监听端口 (默认: 8115)
    GATEWAY_DEBUG: 调试模式 (默认: false)
    STRM_BASE_URL: STRM 文件基础 URL
    CACHE_TTL: 下载链接缓存时间（秒，默认: 3600）
    ENABLE_CORS: 是否启用 CORS (默认: true)
    DB_TYPE: 数据库类型 (sqlite/mysql，默认: sqlite)
    DB_PATH: SQLite 数据库路径 (默认: ~/.strm_gateway.db)
    DB_HOST: MySQL 主机地址 (默认: localhost)
    DB_PORT: MySQL 端口 (默认: 3306)
    DB_NAME: MySQL 数据库名 (默认: strm_gateway)
    DB_USER: MySQL 用户名 (默认: root)
    DB_PASSWORD: MySQL 密码
"""
import argparse
import logging
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import GatewayServer, AppConfig


def main():
    parser = argparse.ArgumentParser(
        description='Multi-Cloud STRM Gateway Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--host', default=None, help='Listen host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None, help='Listen port (default: 8115)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--strm-base-url', default=None, help='Base URL for STRM files')

    args = parser.parse_args()

    # 配置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # 加载配置
    config = AppConfig.from_env()

    if args.host:
        config.gateway.HOST = args.host
    if args.port:
        config.gateway.PORT = args.port
    if args.debug:
        config.gateway.DEBUG = True
    if args.strm_base_url:
        config.gateway.STRM_BASE_URL = args.strm_base_url

    # 启动服务
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              Multi-Cloud STRM Gateway v2.0                   ║
╠══════════════════════════════════════════════════════════════╣
║  Host: {config.gateway.HOST:<54} ║
║  Port: {config.gateway.PORT:<54} ║
║  Debug: {str(config.gateway.DEBUG):<53} ║
║  Database: {config.database.TYPE:<49} ║
╚══════════════════════════════════════════════════════════════╝

API Endpoints:
  基础服务:
    GET  /                      - 服务信息
    GET  /health                - 健康检查
    GET  /stream/{{pick_code}}    - 流媒体重定向

  认证管理:
    GET  /api/auth/qrcode       - 获取认证二维码
    GET  /api/auth/status       - 检查认证状态
    POST /api/auth/exchange     - 交换 Token

  网盘管理:
    GET  /api/drives            - 获取网盘列表
    POST /api/drives            - 添加网盘
    POST /api/drives/remove     - 删除网盘
    POST /api/drives/switch     - 切换当前网盘
    POST /api/drives/update     - 更新网盘信息

  文件操作:
    GET  /api/list              - 文件列表
    GET  /api/search            - 文件搜索
    GET  /api/info              - 文件信息
    GET  /api/download          - 获取下载链接

  任务管理:
    GET  /api/tasks             - 获取任务列表
    POST /api/tasks             - 创建任务
    GET  /api/tasks/{{id}}        - 获取任务详情
    PUT  /api/tasks/{{id}}        - 更新任务
    POST /api/tasks/{{id}}/delete - 删除任务
    POST /api/tasks/{{id}}/execute - 手动执行任务

  调度器管理:
    GET  /api/scheduler/status  - 获取调度器状态
    POST /api/scheduler/start   - 启动调度器
    POST /api/scheduler/stop    - 停止调度器

Web 界面: http://localhost:3000 (需要单独启动前端服务)

Press Ctrl+C to stop the server.
""")

    server = GatewayServer(config)
    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
