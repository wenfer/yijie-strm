#!/usr/bin/env python3
"""
115 STRM 网关服务启动脚本

使用方法:
    python run_gateway.py                    # 默认配置启动
    python run_gateway.py --port 8080        # 指定端口
    python run_gateway.py --debug            # 调试模式

环境变量:
    GATEWAY_HOST: 监听地址 (默认: 0.0.0.0)
    GATEWAY_PORT: 监听端口 (默认: 8115)
    STRM_BASE_URL: STRM 文件基础 URL
    RCLONE_TOKEN_PATH: rclone Token 文件路径
    CACHE_TTL: 下载链接缓存时间（秒）
"""
import argparse
import logging
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib115 import GatewayServer, AppConfig


def main():
    parser = argparse.ArgumentParser(
        description='115 STRM Gateway Server',
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
║                    115 STRM Gateway                          ║
╠══════════════════════════════════════════════════════════════╣
║  Host: {config.gateway.HOST:<54} ║
║  Port: {config.gateway.PORT:<54} ║
║  Debug: {str(config.gateway.DEBUG):<53} ║
╚══════════════════════════════════════════════════════════════╝

API Endpoints:
  GET  /                      - 服务信息
  GET  /health                - 健康检查
  GET  /stream/{{pick_code}}    - 流媒体重定向
  GET  /api/list              - 文件列表
  GET  /api/search            - 文件搜索
  GET  /api/info              - 文件信息
  GET  /api/download          - 下载链接
  POST /api/strm/generate     - 生成 STRM 文件
  POST /api/strm/sync         - 同步 STRM 文件

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
