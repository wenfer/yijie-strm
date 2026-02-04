"""
系统 API 路由
"""
import logging
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query

from app.api.schemas import DataResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["系统"])


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0"
    }


@router.get("/info", response_model=DataResponse)
async def system_info():
    """获取系统信息"""
    import platform
    import sys
    
    return DataResponse(data={
        "name": "多网盘 STRM 网关",
        "version": "3.0.0",
        "python_version": sys.version,
        "platform": platform.platform(),
        "start_time": datetime.now().isoformat()
    })


@router.get("/directories", response_model=DataResponse)
async def list_directories(
    path: str = Query("/", description="要浏览的目录路径")
):
    """浏览服务器本地目录"""
    try:
        dir_path = Path(path).expanduser().resolve()

        if not dir_path.exists():
            return DataResponse(success=False, message=f"路径不存在: {path}")

        if not dir_path.is_dir():
            return DataResponse(success=False, message=f"不是一个目录: {path}")

        dirs = []
        try:
            for item in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                if item.is_dir() and not item.name.startswith('.'):
                    dirs.append({
                        "name": item.name,
                        "path": str(item),
                    })
        except PermissionError:
            return DataResponse(success=False, message=f"没有权限访问: {path}")

        return DataResponse(data={
            "current_path": str(dir_path),
            "parent_path": str(dir_path.parent) if dir_path != dir_path.parent else None,
            "directories": dirs,
        })
    except Exception as e:
        logger.error(f"Failed to list directories: {e}")
        return DataResponse(success=False, message=f"浏览目录失败: {str(e)}")
