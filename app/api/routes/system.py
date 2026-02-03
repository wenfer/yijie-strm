"""
系统 API 路由
"""
import logging
import time
from datetime import datetime

from fastapi import APIRouter

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
