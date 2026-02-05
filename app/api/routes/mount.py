from fastapi import APIRouter, HTTPException

from app.api.schemas import MountCreate, ResponseBase
from app.models.mount import Mount
from app.models.drive import Drive
from app.services.mount_service import mount_service

router = APIRouter(prefix="/mounts", tags=["mounts"])

@router.get("")
async def list_mounts():
    """获取挂载列表"""
    mounts = await Mount.all().order_by("-created_at")

    # 同步状态
    results = []
    for mount in mounts:
        # Check if actually running
        status_info = await mount_service.get_mount_status(mount)
        real_status = status_info.get("is_mounted", False)
        if real_status != mount.is_mounted:
            # Update DB to reflect reality
            mount.is_mounted = real_status
            await mount.save()
        results.append(await mount.to_dict())

    return results

@router.post("")
async def create_mount(mount_in: MountCreate):
    """创建挂载点"""
    drive = await Drive.get_or_none(id=mount_in.drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    # 检查挂载点是否已存在
    existing = await Mount.filter(mount_point=mount_in.mount_point).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mount point already exists")

    mount = await Mount.create(
        drive=drive,
        mount_point=mount_in.mount_point,
        mount_config=mount_in.mount_config or {}
    )
    return await mount.to_dict()

@router.post("/{mount_id}/mount")
async def start_mount(mount_id: str):
    """启动挂载

    Returns:
        {
            "success": bool,
            "message": str,
            "logs": [...],  # 启动过程中的日志
            "error": str,   # 如果有错误
            "pid": int,     # 进程ID
            "pending": bool # 是否还在启动中
        }
    """
    mount = await Mount.get_or_none(id=mount_id)
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")

    result = await mount_service.start_mount(mount)

    # 如果失败，返回 500 错误
    if not result.get("success"):
        # 返回详细错误信息和日志
        raise HTTPException(
            status_code=500,
            detail={
                "message": result.get("message"),
                "error": result.get("error"),
                "logs": result.get("logs", [])
            }
        )

    return result

@router.post("/{mount_id}/unmount")
async def stop_mount(mount_id: str):
    """停止挂载

    Returns:
        {
            "success": bool,
            "message": str,
            "logs": [...]  # 停止前的日志
        }
    """
    mount = await Mount.get_or_none(id=mount_id)
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")

    result = await mount_service.stop_mount(mount)
    return result

@router.delete("/{mount_id}", response_model=ResponseBase)
async def delete_mount(mount_id: str):
    """删除挂载配置"""
    mount = await Mount.get_or_none(id=mount_id)
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")

    # 如果正在运行，先停止
    status = await mount_service.get_mount_status(mount)
    if status.get("is_mounted"):
        await mount_service.stop_mount(mount)

    await mount.delete()
    return ResponseBase(success=True, message="Mount deleted")


@router.get("/{mount_id}/logs")
async def get_mount_logs(mount_id: str, limit: int = 100):
    """获取挂载日志

    Args:
        mount_id: 挂载ID
        limit: 返回的日志条数，默认100条

    Returns:
        {
            "logs": [
                {"timestamp": str, "level": str, "message": str},
                ...
            ]
        }
    """
    mount = await Mount.get_or_none(id=mount_id)
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")

    logs = await mount_service.get_mount_logs(mount_id, limit)
    return {"logs": logs}


@router.get("/{mount_id}/status")
async def get_mount_status_endpoint(mount_id: str):
    """获取挂载状态

    Returns:
        {
            "is_mounted": bool,
            "status": str,      # running, starting, failed, stopped
            "pid": int,
            "error": str,       # 如果有错误
            "logs": [...]       # 最近的日志
        }
    """
    mount = await Mount.get_or_none(id=mount_id)
    if not mount:
        raise HTTPException(status_code=404, detail="Mount not found")

    status = await mount_service.get_mount_status(mount)
    return status
