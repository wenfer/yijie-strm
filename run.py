#!/usr/bin/env python3
"""
多网盘 STRM 网关服务启动脚本 v3.0

基于 FastAPI + Tortoise ORM + p115client 构建

使用方法:
    python run.py                    # 默认配置启动
    python run.py --port 8080        # 指定端口
    python run.py --debug            # 调试模式

环境变量:
    GATEWAY_HOST: 监听地址 (默认: 0.0.0.0)
    GATEWAY_PORT: 监听端口 (默认: 8115)
    GATEWAY_DEBUG: 调试模式 (默认: false)
    DB_URL: 数据库 URL (默认: sqlite://~/.strm_gateway.db)
    LOG_LEVEL: 日志级别 (默认: INFO)

示例数据库 URL:
    SQLite: sqlite://db.sqlite3
    MySQL: mysql://user:password@localhost:3306/dbname
"""
import argparse
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description='Multi-Cloud STRM Gateway Server v3.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--host', default=None, help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None, help='监听端口 (默认: 8115)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--reload', action='store_true', help='启用热重载')
    
    args = parser.parse_args()
    
    # 设置环境变量
    if args.host:
        os.environ['GATEWAY_HOST'] = args.host
    if args.port:
        os.environ['GATEWAY_PORT'] = str(args.port)
    if args.debug:
        os.environ['GATEWAY_DEBUG'] = 'true'
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # 导入配置
    from app.core.config import get_settings
    settings = get_settings()
    
    # 覆盖参数
    if args.host:
        settings.gateway.host = args.host
    if args.port:
        settings.gateway.port = args.port
    if args.debug:
        settings.gateway.debug = True
        settings.log.level = 'DEBUG'
    
    # 显示启动信息
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              Multi-Cloud STRM Gateway v3.0                   ║
╠══════════════════════════════════════════════════════════════╣
║  Python: {sys.version.split()[0]:<51} ║
║  Host: {settings.gateway.host:<54} ║
║  Port: {settings.gateway.port:<54} ║
║  Debug: {str(settings.gateway.debug):<53} ║
║  Database: {settings.database.url:<50} ║
╚══════════════════════════════════════════════════════════════╝

API 文档: http://{settings.gateway.host}:{settings.gateway.port}/docs
Health:  http://{settings.gateway.host}:{settings.gateway.port}/api/system/health

Press Ctrl+C to stop the server.
""")
    
    # 启动服务
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.gateway.host,
        port=settings.gateway.port,
        reload=args.reload or settings.gateway.debug,
        log_level=settings.log.level.lower()
    )


if __name__ == '__main__':
    main()
