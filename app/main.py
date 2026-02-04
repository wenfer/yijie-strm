"""
FastAPI 主应用入口

多网盘 STRM 网关系统 v3.0
基于 FastAPI + Tortoise ORM + p115client 构建
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from tortoise import Tortoise

from app.core.config import get_settings
from app.api.routes import drive, auth, file, task, stream, system, scheduler as scheduler_router
from app.api.routes.file import compat_router as file_compat_router
from app.tasks.scheduler import scheduler

# 获取配置
settings = get_settings()

# 确保数据目录存在
settings.data_dir.mkdir(parents=True, exist_ok=True)

# 配置日志
log_file = settings.data_dir / "app.log"
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(settings.log.format))

logging.basicConfig(
    level=getattr(logging, settings.log.level.upper()),
    format=settings.log.format,
    handlers=[
        logging.StreamHandler(),
        file_handler
    ]
)
logger = logging.getLogger(__name__)


async def init_tortoise():
    """初始化 Tortoise ORM"""
    database_url = settings.database.url
    if database_url.startswith("sqlite://"):
        # 处理 SQLite 路径
        db_path = database_url.replace("sqlite://", "")
        if db_path.startswith("~/"):
            db_path = os.path.expanduser(db_path)
        database_url = f"sqlite://{db_path}"

    await Tortoise.init(
        db_url=database_url,
        modules={"models": ["app.models"]}
    )

    if settings.database.generate_schemas:
        await Tortoise.generate_schemas()

    logger.info("Tortoise ORM initialized")


async def close_tortoise():
    """关闭 Tortoise ORM"""
    await Tortoise.close_connections()
    logger.info("Tortoise ORM closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动
    logger.info("Starting STRM Gateway...")

    # 确保数据目录存在
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # 初始化数据库
    await init_tortoise()

    # 启动调度器
    await scheduler.start()

    logger.info("STRM Gateway started successfully")

    yield

    # 关闭
    logger.info("Shutting down STRM Gateway...")

    # 停止调度器
    await scheduler.stop()

    # 关闭数据库
    await close_tortoise()

    logger.info("STRM Gateway shut down successfully")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用

    Returns:
        FastAPI 应用实例
    """
    app = FastAPI(
        title="多网盘 STRM 网关",
        description="基于 FastAPI + Tortoise ORM + p115client 构建的多网盘 STRM 文件生成和流媒体网关",
        version="3.0.0",
        lifespan=lifespan
    )

    # CORS 中间件
    if settings.gateway.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.gateway.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 注册路由
    app.include_router(drive.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(file.router, prefix="/api")
    app.include_router(file_compat_router, prefix="/api")  # 兼容旧版文件 API
    app.include_router(task.router, prefix="/api")
    app.include_router(stream.router)
    app.include_router(system.router, prefix="/api")
    app.include_router(scheduler_router.router, prefix="/api")

    # 挂载前端静态文件 (如果存在)
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        logger.info(f"Mounting static files from {static_dir}")

        # 挂载静态资源 (_next, images, etc.)
        app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="next-static")

        # 处理根路径和其他前端路由
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            """
            服务前端页面
            - 如果是 API 路径，会被上面的路由拦截
            - 如果是静态文件，返回对应文件
            - 否则返回 index.html (SPA 路由)
            """
            # 检查是否是静态文件
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(file_path)

            # 返回 index.html 用于前端路由
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)

            # 如果没有前端文件，返回 API 信息
            return {
                "name": "多网盘 STRM 网关",
                "version": "3.0.0",
                "docs": "/docs",
                "endpoints": {
                    "health": "/api/system/health",
                    "drives": "/api/drives",
                    "auth": "/api/auth",
                    "files": "/api/files",
                    "tasks": "/api/tasks",
                    "stream": "/stream/{pick_code}"
                }
            }
    else:
        logger.warning("Static files not found, frontend will not be served")

        # 根路由
        @app.get("/")
        async def root():
            return {
                "name": "多网盘 STRM 网关",
                "version": "3.0.0",
                "docs": "/docs",
                "endpoints": {
                    "health": "/api/system/health",
                    "drives": "/api/drives",
                    "auth": "/api/auth",
                    "files": "/api/files",
                    "tasks": "/api/tasks",
                    "stream": "/stream/{pick_code}"
                }
            }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.gateway.host,
        port=settings.gateway.port,
        reload=settings.gateway.debug,
        log_level=settings.log.level.lower()
    )
