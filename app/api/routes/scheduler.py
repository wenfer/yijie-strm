"""
调度器管理 API 路由
"""
import logging
from fastapi import APIRouter, HTTPException

from app.tasks.scheduler import scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduler", tags=["调度器管理"])


@router.get("/status")
async def get_scheduler_status():
    """获取调度器状态"""
    try:
        status = scheduler.get_status()
        return {
            "success": True,
            "scheduler": {
                "running": status["running"],
                "scheduled_tasks": status["tasks_count"],
                "running_tasks": len(scheduler._running_tasks),
                "watch_tasks": 0  # 暂无监听任务统计
            }
        }
    except Exception as e:
        logger.exception(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_scheduler():
    """启动调度器"""
    try:
        await scheduler.start()
        return {"success": True, "message": "调度器已启动"}
    except Exception as e:
        logger.exception(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """停止调度器"""
    try:
        await scheduler.stop()
        return {"success": True, "message": "调度器已停止"}
    except Exception as e:
        logger.exception(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))
