"""
CloudDrive2 兼容 API 路由

提供与 CloudDrive2 兼容的 API 接口，用于替换其他系统中使用 CloudDrive2 的服务地址。

兼容的端点：
- POST /api/files/offsline/download - 添加离线下载任务
- GET  /api/files/offsline/list - 获取离线任务列表  
- DELETE /api/files/offsline/remove - 删除离线任务
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from app.services.drive_service import DriveService
from app.core.exceptions import DriveNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["CloudDrive2兼容"])


def get_drive_service() -> DriveService:
    """获取 DriveService 实例"""
    from app.core.config import get_settings
    settings = get_settings()
    return DriveService(settings.data_dir)


async def get_provider(drive_id: Optional[str] = None):
    """获取 Provider 实例"""
    drive_service = get_drive_service()
    
    # 如果没有指定 drive_id，使用当前网盘
    if not drive_id:
        drive = await drive_service.get_current_drive()
        if not drive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有指定网盘且没有设置默认网盘"
            )
        drive_id = drive.id
    
    # 获取 provider
    try:
        provider = await drive_service.get_provider(drive_id)
    except DriveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"网盘不存在: {drive_id}"
        )
    
    # 检查认证状态
    if not await provider.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="网盘未认证或认证已过期，请重新扫码登录"
        )
    
    return provider


# ==================== CloudDrive2 请求/响应模型 ====================

class CD2OfflineDownloadRequest(BaseModel):
    """CloudDrive2 离线下载请求"""
    path: str = Field(default="/", description="保存路径")
    url: str = Field(..., description="下载链接 (HTTP/HTTPS/磁力链/电驴)")
    type: Optional[str] = Field(default="0", description="任务类型(可选)")
    name: Optional[str] = Field(default=None, description="任务名称(可选)")


class CD2OfflineTask(BaseModel):
    """CloudDrive2 离线任务信息"""
    taskId: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    size: int = Field(default=0, description="文件大小")
    status: str = Field(..., description="任务状态: pending/downloading/completed/failed")
    progress: float = Field(default=0.0, description="下载进度 0-100")
    speed: int = Field(default=0, description="下载速度(字节/秒)")
    createTime: int = Field(default=0, description="创建时间戳")
    url: str = Field(default="", description="下载链接")


class CD2BaseResponse(BaseModel):
    """CloudDrive2 基础响应"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(default=None, description="消息")
    data: Optional[Any] = Field(default=None, description="数据")


# ==================== CloudDrive2 兼容端点 ====================

@router.post("/api/files/offsline/download", response_model=CD2BaseResponse)
@router.post("/api/files/offline_download", response_model=CD2BaseResponse)
async def cd2_offline_download(
    request: CD2OfflineDownloadRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 添加离线下载任务
    
    兼容 CloudDrive2 的离线下载 API，支持以下链接类型：
    - HTTP/HTTPS: 普通下载链接
    - 磁力链(magnet:): 如 magnet:?xt=urn:btih:...
    - 电驴(ed2k:): 如 ed2k://|file|...
    
    请求示例：
    ```json
    {
        "path": "/downloads",
        "url": "magnet:?xt=urn:btih:...",
        "type": "0"
    }
    ```
    """
    try:
        provider = await get_provider(drive_id)
        
        # 添加任务
        resp = await provider.offline_add_url(
            url=request.url,
            save_cid=None  # 使用默认保存路径
        )
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "添加任务失败")
            errno = resp.get("errno", 0)
            if errno == 10008:
                error_msg = "任务已存在"
            elif errno == 10009:
                error_msg = "无效的下载链接"
            elif errno == 10010:
                error_msg = "存储空间不足"
            
            logger.warning(f"CD2 compat: Add task failed: {error_msg}")
            return CD2BaseResponse(
                success=False,
                message=error_msg
            )
        
        # 返回 CloudDrive2 格式响应
        return CD2BaseResponse(
            success=True,
            message="添加任务成功",
            data={
                "taskId": resp.get("info_hash", ""),
                "name": resp.get("name", request.name or ""),
                "url": request.url,
                "path": request.path,
                "status": "pending"
            }
        )
        
    except HTTPException as e:
        return CD2BaseResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CD2 compat: Error adding offline task: {e}")
        return CD2BaseResponse(
            success=False,
            message=f"添加任务失败: {str(e)}"
        )


@router.get("/api/files/offsline/list", response_model=CD2BaseResponse)
@router.get("/api/files/offline_list", response_model=CD2BaseResponse)
async def cd2_offline_list(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 获取离线任务列表
    
    返回 CloudDrive2 格式的任务列表
    """
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_list(page=page, per_page=size)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "获取任务列表失败")
            return CD2BaseResponse(
                success=False,
                message=error_msg
            )
        
        # 转换任务格式为 CloudDrive2 格式
        status_map = {
            0: "pending",
            1: "downloading",
            2: "completed",
            -1: "failed"
        }
        
        tasks = []
        for task in resp.get("tasks", []):
            # 计算进度
            file_size = int(task.get("file_size", 0) or 0)
            received = int(task.get("received", 0) or 0)
            progress = 0.0
            if file_size > 0:
                progress = round(received * 100 / file_size, 2)
            
            tasks.append({
                "taskId": task.get("info_hash", ""),
                "name": task.get("name", ""),
                "size": int(task.get("size", 0) or 0),
                "status": status_map.get(task.get("status", 0), "unknown"),
                "progress": progress,
                "speed": int(task.get("speed", 0) or 0),
                "createTime": int(task.get("create_time", 0) or 0),
                "url": task.get("url", "")
            })
        
        return CD2BaseResponse(
            success=True,
            data={
                "tasks": tasks,
                "total": resp.get("count", len(tasks)),
                "page": page,
                "size": size
            }
        )
        
    except HTTPException as e:
        return CD2BaseResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CD2 compat: Error getting offline list: {e}")
        return CD2BaseResponse(
            success=False,
            message=f"获取任务列表失败: {str(e)}"
        )


@router.delete("/api/files/offsline/remove", response_model=CD2BaseResponse)
@router.delete("/api/files/offline_remove", response_model=CD2BaseResponse)
async def cd2_offline_remove(
    taskId: str,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 删除离线任务
    
    参数：
    - taskId: 任务ID (info_hash)
    """
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_remove([taskId])
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "删除任务失败")
            return CD2BaseResponse(
                success=False,
                message=error_msg
            )
        
        return CD2BaseResponse(
            success=True,
            message="删除任务成功"
        )
        
    except HTTPException as e:
        return CD2BaseResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CD2 compat: Error removing offline task: {e}")
        return CD2BaseResponse(
            success=False,
            message=f"删除任务失败: {str(e)}"
        )


@router.get("/api/files/offsline/clear", response_model=CD2BaseResponse)
@router.get("/api/files/offline_clear", response_model=CD2BaseResponse)
async def cd2_offline_clear(
    status: int = Query(0, ge=0, le=2, description="0=已完成, 1=全部, 2=失败"),
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 清空离线任务
    
    参数：
    - status: 0=清空已完成, 1=清空全部, 2=清空失败
    """
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_clear(status)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "清空任务失败")
            return CD2BaseResponse(
                success=False,
                message=error_msg
            )
        
        status_text = {0: "已完成", 1: "所有", 2: "失败"}.get(status, "未知")
        return CD2BaseResponse(
            success=True,
            message=f"已清空{status_text}任务"
        )
        
    except HTTPException as e:
        return CD2BaseResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CD2 compat: Error clearing offline tasks: {e}")
        return CD2BaseResponse(
            success=False,
            message=f"清空任务失败: {str(e)}"
        )


# ==================== 兼容路径映射 ====================
# CloudDrive2 常用的其他变体路径

@router.post("/cd2/offline_download", response_model=CD2BaseResponse)
async def cd2_offline_download_alt(
    request: CD2OfflineDownloadRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """CloudDrive2 兼容接口 - 添加离线下载任务 (简化路径)"""
    return await cd2_offline_download(request, drive_id)


@router.get("/cd2/offline_list", response_model=CD2BaseResponse)
async def cd2_offline_list_alt(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """CloudDrive2 兼容接口 - 获取离线任务列表 (简化路径)"""
    return await cd2_offline_list(page, size, drive_id)
