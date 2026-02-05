"""
任务管理 API 路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, TaskExecute,
    TaskStatistics, DataResponse, ResponseBase
)
from app.services.task_service import TaskService
from app.services.drive_service import DriveService
from app.core.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["任务管理"])


def get_task_service() -> TaskService:
    """获取 TaskService 实例"""
    return TaskService()


def get_drive_service() -> DriveService:
    """获取 DriveService 实例"""
    from app.core.config import get_settings
    settings = get_settings()
    return DriveService(settings.data_dir)


@router.get("")
async def list_tasks(
    drive_id: Optional[str] = None,
    status: Optional[str] = None,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务列表"""
    tasks = await task_service.list_tasks(drive_id, status)
    return {
        "success": True,
        "tasks": [task.to_dict() for task in tasks]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    task_service: TaskService = Depends(get_task_service)
):
    """创建任务"""
    try:
        task = await task_service.create_task(
            name=data.name,
            drive_id=data.drive_id,
            source_cid=data.source_cid,
            output_dir=data.output_dir,
            base_url=data.base_url,
            include_video=data.include_video,
            include_audio=data.include_audio,
            custom_extensions=data.custom_extensions,
            schedule_enabled=data.schedule_enabled,
            schedule_type=data.schedule_type,
            schedule_config=data.schedule_config,
            watch_enabled=data.watch_enabled,
            watch_interval=data.watch_interval,
            delete_orphans=data.delete_orphans,
            preserve_structure=data.preserve_structure,
            overwrite_strm=data.overwrite_strm,
            download_metadata=data.download_metadata
        )
        
        # 如果启用了调度，添加到调度器
        if task.schedule_enabled:
            from app.tasks.scheduler import scheduler
            await scheduler.add_task(task)
        
        return {
            "success": True,
            "task": task.to_dict()
        }
    except Exception as e:
        logger.exception(f"Failed to create task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务详情"""
    try:
        task = await task_service.get_task(task_id)
        return {
            "success": True,
            "task": task.to_dict()
        }
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.post("/{task_id}")
async def update_task_post(
    task_id: str,
    data: dict,
    task_service: TaskService = Depends(get_task_service)
):
    """更新任务（兼容前端 POST 调用方式）"""
    try:
        # 过滤掉 null 值
        updates = {k: v for k, v in data.items() if v is not None}
        
        task = await task_service.update_task(task_id, **updates)
        
        # 如果调度配置改变，重新调度
        if any(k in updates for k in ['schedule_enabled', 'schedule_type', 'schedule_config']):
            from app.tasks.scheduler import scheduler
            await scheduler.remove_task(task_id)
            if task.schedule_enabled:
                await scheduler.add_task(task)
        
        return {
            "success": True,
            "message": "任务更新成功"
        }
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.post("/{task_id}/delete")
async def delete_task_post(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """删除任务（兼容前端 POST 调用方式）"""
    try:
        # 从调度器移除
        from app.tasks.scheduler import scheduler
        await scheduler.remove_task(task_id)
        
        # 删除任务
        await task_service.delete_task(task_id)
        
        return {"success": True, "message": "任务删除成功"}
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: str,
    data: dict = None,
    task_service: TaskService = Depends(get_task_service),
    drive_service: DriveService = Depends(get_drive_service)
):
    """手动执行任务"""
    try:
        task = await task_service.get_task(task_id)
        
        force = data.get("force", False) if data else False
        
        # 检查任务状态
        if task.status == "running" and not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="任务正在运行中"
            )
        
        # 异步执行任务
        from app.tasks.executor import execute_strm_task
        import asyncio
        
        # 获取 provider
        provider = await drive_service.get_provider(task.drive_id)

        # 检查认证状态
        if not await provider.is_authenticated():
            # 如果认证失效，自动重置认证状态
            try:
                await drive_service.reset_auth(task.drive_id)
                logger.info(f"Drive {task.drive_id} authentication expired, reset auth status")
            except Exception as e:
                logger.error(f"Failed to reset auth for drive {task.drive_id}: {e}")

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="网盘未认证或认证已过期，请重新扫码登录"
            )

        # 创建 file_service 和 strm_service
        from app.services.file_service import FileService
        from app.services.strm_service import StrmService
        
        file_service = FileService(provider)
        strm_service = StrmService(
            file_service=file_service,
            provider=provider,
            base_url=task.base_url
        )
        
        # 后台执行任务
        asyncio.create_task(execute_strm_task(task_id, strm_service))
        
        return {"success": True, "message": "任务开始执行"}
        
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to execute task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行任务失败: {str(e)}"
        )


@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务状态"""
    try:
        task = await task_service.get_task(task_id)
        return {
            "success": True,
            "status": task.status,
            "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
            "last_run_status": task.last_run_status,
            "last_run_message": task.last_run_message,
            "next_run_time": None,  # 暂时不支持
            "total_files": task.total_files,
            "current_file_index": task.current_file_index
        }
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.get("/{task_id}/statistics")
async def get_task_statistics(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务统计信息"""
    try:
        stats = await task_service.get_task_statistics(task_id)
        return {
            "success": True,
            "statistics": stats
        }
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    limit: int = 50,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务日志"""
    try:
        logs = await task_service.get_task_logs(task_id, limit)
        return {
            "success": True,
            "logs": [log.to_dict() for log in logs]
        }
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.get("/{task_id}/records")
async def get_task_records(
    task_id: str,
    status: Optional[str] = "active",
    keyword: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    task_service: TaskService = Depends(get_task_service)
):
    """获取任务生成的 STRM 记录"""
    try:
        records = await task_service.get_task_records(task_id, status)
        
        # 客端端筛选
        if keyword:
            records = [r for r in records if keyword.lower() in r.file_name.lower()]
        
        total = len(records)
        records = records[offset:offset + limit]
        
        return {
            "success": True,
            "records": [record.to_dict() for record in records],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}"
        )


@router.delete("/{task_id}/records/{record_id}")
async def delete_task_record(
    task_id: str,
    record_id: str,
    delete_file: bool = True,
    task_service: TaskService = Depends(get_task_service)
):
    """删除单个 STRM 记录"""
    try:
        await task_service.delete_task_record(task_id, record_id, delete_file)
        return {
            "success": True,
            "message": f"记录已删除"
        }
    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Failed to delete record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除记录失败: {str(e)}"
        )


@router.post("/{task_id}/records/batch-delete")
async def batch_delete_task_records(
    task_id: str,
    data: dict,
    task_service: TaskService = Depends(get_task_service)
):
    """批量删除 STRM 记录"""
    try:
        record_ids = data.get("record_ids", [])
        delete_files = data.get("delete_files", True)
        
        deleted_count = await task_service.delete_task_records(
            task_id, record_ids if record_ids else None, delete_files
        )
        
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条记录",
            "deleted_count": deleted_count
        }
    except TaskNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Failed to batch delete records: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除失败: {str(e)}"
        )
