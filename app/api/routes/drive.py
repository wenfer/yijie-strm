"""
网盘管理 API 路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas import (
    DriveCreate, DriveUpdate, DriveResponse,
    ResponseBase, DataResponse
)
from app.services.drive_service import DriveService
from app.core.exceptions import DriveNotFoundError, ConflictError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drives", tags=["网盘管理"])


async def get_drive_service() -> DriveService:
    """获取 DriveService 实例"""
    from app.core.config import get_settings
    settings = get_settings()
    return DriveService(settings.data_dir)


@router.get("")
async def list_drives(
    drive_service: DriveService = Depends(get_drive_service)
):
    """获取网盘列表"""
    drives = await drive_service.list_drives()
    return {
        "success": True,
        "drives": [drive.to_dict() for drive in drives]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_drive(
    data: DriveCreate,
    drive_service: DriveService = Depends(get_drive_service)
):
    """创建网盘"""
    try:
        drive = await drive_service.create_drive(
            name=data.name,
            drive_type=data.drive_type
        )
        return {
            "success": True,
            "drive": drive.to_dict()
        }
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/current", response_model=DataResponse)
async def get_current_drive(
    drive_service: DriveService = Depends(get_drive_service)
):
    """获取当前默认网盘"""
    drive = await drive_service.get_current_drive()
    if not drive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有设置默认网盘"
        )
    return DataResponse(data=drive.to_dict())


@router.post("/switch")
async def switch_drive_by_body(
    data: dict,
    drive_service: DriveService = Depends(get_drive_service)
):
    """切换当前网盘（兼容前端调用方式）"""
    drive_id = data.get("drive_id")
    if not drive_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 drive_id")
    try:
        await drive_service.set_current_drive(drive_id)
        return {"success": True, "message": "切换成功"}
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )


@router.post("/{drive_id}/switch", response_model=ResponseBase)
async def switch_drive(
    drive_id: str,
    drive_service: DriveService = Depends(get_drive_service)
):
    """切换当前网盘"""
    try:
        await drive_service.set_current_drive(drive_id)
        return ResponseBase(message="切换成功")
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )


@router.post("/update")
async def update_drive_by_body(
    data: dict,
    drive_service: DriveService = Depends(get_drive_service)
):
    """更新网盘信息（兼容前端调用方式）"""
    drive_id = data.get("drive_id")
    name = data.get("name")
    if not drive_id or not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 drive_id 或 name")
    try:
        drive = await drive_service.update_drive(
            drive_id=drive_id,
            name=name
        )
        return {"success": True, "message": "更新成功"}
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{drive_id}/update", response_model=DataResponse)
async def update_drive(
    drive_id: str,
    data: DriveUpdate,
    drive_service: DriveService = Depends(get_drive_service)
):
    """更新网盘信息"""
    try:
        drive = await drive_service.update_drive(
            drive_id=drive_id,
            name=data.name
        )
        return DataResponse(
            message="更新成功",
            data=drive.to_dict()
        )
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/remove")
async def remove_drive_by_body(
    data: dict,
    drive_service: DriveService = Depends(get_drive_service)
):
    """删除网盘（兼容前端调用方式）"""
    drive_id = data.get("drive_id")
    if not drive_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 drive_id")
    try:
        await drive_service.delete_drive(drive_id)
        return {"success": True, "message": "删除成功"}
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )


@router.delete("/{drive_id}", response_model=ResponseBase)
async def delete_drive(
    drive_id: str,
    drive_service: DriveService = Depends(get_drive_service)
):
    """删除网盘"""
    try:
        await drive_service.delete_drive(drive_id)
        return ResponseBase(message="删除成功")
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )


@router.get("/{drive_id}/status", response_model=DataResponse)
async def get_drive_status(
    drive_id: str,
    drive_service: DriveService = Depends(get_drive_service)
):
    """获取网盘认证状态"""
    try:
        is_authenticated = await drive_service.check_authenticated(drive_id)
        return DataResponse(data={
            "drive_id": drive_id,
            "authenticated": is_authenticated
        })
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )
