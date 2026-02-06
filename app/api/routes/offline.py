"""
云下载（离线下载）API 路由

支持浏览和添加云下载任务
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.schemas import (
    ResponseBase, DataResponse,
    OfflineTaskItem, OfflineListResponse,
    OfflineAddUrlRequest, OfflineAddUrlsRequest,
    OfflineAddTorrentRequest, OfflineRemoveRequest,
    OfflineRestartRequest, OfflineClearRequest,
    OfflineQuotaInfo, OfflineTaskCount, OfflineDownloadPath
)
from app.services.drive_service import DriveService
from app.core.exceptions import DriveNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/offline", tags=["云下载"])


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


def _format_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    else:
        return f"{size / (1024 ** 3):.2f} GB"


def _format_speed(speed: int) -> str:
    """格式化下载速度"""
    if speed < 1024:
        return f"{speed} B/s"
    elif speed < 1024 ** 2:
        return f"{speed / 1024:.2f} KB/s"
    else:
        return f"{speed / (1024 ** 2):.2f} MB/s"


def _format_timestamp(timestamp: int) -> str:
    """格式化时间戳"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ""


def _get_status_text(status: int) -> str:
    """获取状态文本"""
    status_map = {
        0: "等待下载",
        1: "下载中",
        2: "已完成",
        -1: "失败",
        3: "未知"
    }
    return status_map.get(status, "未知")


def _parse_task_item(task: dict) -> OfflineTaskItem:
    """解析任务数据"""
    size = int(task.get("size", 0) or 0)
    status = int(task.get("status", 0) or 0)
    create_time = int(task.get("create_time", 0) or 0)
    update_time = int(task.get("update_time", 0) or 0)
    speed = int(task.get("speed", 0) or 0)
    
    # 计算进度
    file_size = int(task.get("file_size", 0) or 0)
    received = int(task.get("received", 0) or 0)
    progress = 0.0
    if file_size > 0:
        progress = round(received * 100 / file_size, 2)
    
    return OfflineTaskItem(
        info_hash=task.get("info_hash", ""),
        name=task.get("name", ""),
        size=size,
        size_formatted=_format_size(size),
        status=status,
        status_text=_get_status_text(status),
        progress=progress,
        speed=speed,
        speed_formatted=_format_speed(speed),
        create_time=create_time,
        create_time_formatted=_format_timestamp(create_time),
        update_time=update_time,
        update_time_formatted=_format_timestamp(update_time),
        save_cid=task.get("save_cid"),
        url=task.get("url"),
        del_file=int(task.get("del_file", 0) or 0)
    )


@router.get("/list", response_model=OfflineListResponse)
async def offline_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """获取云下载任务列表"""
    try:
        provider = await get_provider(drive_id)
        resp = await provider.offline_list(page=page, per_page=per_page)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "获取任务列表失败")
            logger.error(f"Failed to get offline list: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # 解析任务列表
        tasks_data = resp.get("tasks", [])
        tasks = [_parse_task_item(t) for t in tasks_data]
        
        return OfflineListResponse(
            success=True,
            page=page,
            per_page=per_page,
            total=resp.get("count", len(tasks)),
            tasks=tasks
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting offline list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取云下载任务列表失败: {str(e)}"
        )


@router.post("/add-url", response_model=DataResponse)
async def offline_add_url(
    request: OfflineAddUrlRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """添加 URL 云下载任务
    
    支持链接类型：
    - HTTP/HTTPS: 普通下载链接
    - 磁力链(magnet:): 磁力链接
    - 电驴(ed2k:): 电驴链接
    """
    try:
        provider = await get_provider(drive_id)
        
        # 添加任务
        resp = await provider.offline_add_url(
            url=request.url,
            save_cid=request.save_cid
        )
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "添加任务失败")
            # 处理特定错误码
            errno = resp.get("errno", 0)
            if errno == 10008:
                error_msg = "任务已存在"
            elif errno == 10009:
                error_msg = "无效的下载链接"
            elif errno == 10010:
                error_msg = "存储空间不足"
            
            logger.error(f"Failed to add offline URL: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return DataResponse(
            success=True,
            message="添加云下载任务成功",
            data={
                "info_hash": resp.get("info_hash"),
                "name": resp.get("name"),
                "url": request.url
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding offline URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加云下载任务失败: {str(e)}"
        )


@router.post("/add-urls", response_model=DataResponse)
async def offline_add_urls(
    request: OfflineAddUrlsRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """批量添加 URL 云下载任务"""
    try:
        provider = await get_provider(drive_id)
        
        if not request.urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="下载链接列表不能为空"
            )
        
        # 批量添加
        resp = await provider.offline_add_urls(
            urls=request.urls,
            save_cid=request.save_cid
        )
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "批量添加任务失败")
            logger.error(f"Failed to add offline URLs: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # 解析结果
        result = resp.get("result", [])
        success_count = sum(1 for r in result if r.get("state", False))
        
        return DataResponse(
            success=True,
            message=f"批量添加完成: 成功 {success_count}/{len(request.urls)}",
            data={
                "total": len(request.urls),
                "success": success_count,
                "failed": len(request.urls) - success_count,
                "results": result
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding offline URLs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量添加云下载任务失败: {str(e)}"
        )


@router.post("/add-torrent", response_model=DataResponse)
async def offline_add_torrent(
    request: OfflineAddTorrentRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """添加种子云下载任务"""
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_add_torrent(
            torrent_path=request.torrent_path,
            save_cid=request.save_cid
        )
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "添加种子任务失败")
            logger.error(f"Failed to add offline torrent: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return DataResponse(
            success=True,
            message="添加种子任务成功",
            data={
                "info_hash": resp.get("info_hash"),
                "name": resp.get("name")
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding offline torrent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加种子任务失败: {str(e)}"
        )


@router.post("/remove", response_model=ResponseBase)
async def offline_remove(
    request: OfflineRemoveRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """删除云下载任务"""
    try:
        provider = await get_provider(drive_id)
        
        if not request.info_hashes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务info_hash列表不能为空"
            )
        
        resp = await provider.offline_remove(request.info_hashes)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "删除任务失败")
            logger.error(f"Failed to remove offline tasks: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ResponseBase(
            success=True,
            message=f"成功删除 {len(request.info_hashes)} 个任务"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error removing offline tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除云下载任务失败: {str(e)}"
        )


@router.post("/clear", response_model=ResponseBase)
async def offline_clear(
    request: OfflineClearRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """清空云下载任务
    
    - status=0: 清空已完成任务
    - status=1: 清空所有任务
    - status=2: 清空失败任务
    """
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_clear(request.status)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "清空任务失败")
            logger.error(f"Failed to clear offline tasks: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        status_text = {0: "已完成", 1: "所有", 2: "失败"}.get(request.status, "未知")
        return ResponseBase(
            success=True,
            message=f"成功清空{status_text}任务"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error clearing offline tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空云下载任务失败: {str(e)}"
        )


@router.post("/restart", response_model=ResponseBase)
async def offline_restart(
    request: OfflineRestartRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """重新启动云下载任务"""
    try:
        provider = await get_provider(drive_id)
        
        if not request.info_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务info_hash不能为空"
            )
        
        resp = await provider.offline_restart(request.info_hash)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "重启任务失败")
            logger.error(f"Failed to restart offline task: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ResponseBase(
            success=True,
            message="重启任务成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error restarting offline task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启云下载任务失败: {str(e)}"
        )


@router.get("/quota", response_model=DataResponse)
async def offline_quota(
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """获取云下载配额信息"""
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_quota_info()
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "获取配额信息失败")
            logger.error(f"Failed to get offline quota: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # 解析配额信息
        total = int(resp.get("total", 0) or 0)
        used = int(resp.get("used", 0) or 0)
        
        quota_info = OfflineQuotaInfo(
            total=total,
            used=used,
            remaining=total - used,
            total_formatted=_format_size(total),
            used_formatted=_format_size(used),
            remaining_formatted=_format_size(total - used)
        )
        
        return DataResponse(
            success=True,
            data=quota_info.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting offline quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取云下载配额信息失败: {str(e)}"
        )


@router.get("/count", response_model=DataResponse)
async def offline_count(
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """获取云下载任务数量统计"""
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_task_count()
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "获取任务数量失败")
            logger.error(f"Failed to get offline count: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # 解析数量统计
        count_data = resp.get("count", {})
        task_count = OfflineTaskCount(
            total=int(count_data.get("total", 0) or 0),
            downloading=int(count_data.get("downloading", 0) or 0),
            completed=int(count_data.get("completed", 0) or 0),
            failed=int(count_data.get("failed", 0) or 0),
            pending=int(count_data.get("pending", 0) or 0)
        )
        
        return DataResponse(
            success=True,
            data=task_count.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting offline count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取云下载任务数量失败: {str(e)}"
        )


@router.get("/download-path", response_model=DataResponse)
async def offline_download_path(
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """获取云下载默认保存路径"""
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_download_path()
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "获取下载路径失败")
            logger.error(f"Failed to get download path: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        path_info = OfflineDownloadPath(
            cid=resp.get("cid", ""),
            name=resp.get("name", ""),
            path=resp.get("path", "")
        )
        
        return DataResponse(
            success=True,
            data=path_info.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting download path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取云下载默认路径失败: {str(e)}"
        )


@router.post("/download-path", response_model=ResponseBase)
async def offline_set_download_path(
    cid: str,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """设置云下载默认保存路径"""
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_download_path_set(cid)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "设置下载路径失败")
            logger.error(f"Failed to set download path: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        return ResponseBase(
            success=True,
            message="设置云下载默认路径成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error setting download path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置云下载默认路径失败: {str(e)}"
        )


# ==================== CloudDrive2 兼容接口 ====================


class CloudDrive2OfflineRequest(BaseModel):
    """CloudDrive2 离线下载请求格式"""
    path: str = Field(..., description="保存路径")
    url: str = Field(..., description="下载链接")
    type: Optional[str] = Field("0", description="任务类型")
    name: Optional[str] = Field(None, description="任务名称(可选)")


class CloudDrive2OfflineResponse(BaseModel):
    """CloudDrive2 离线下载响应格式"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.post("/cd2/download", response_model=CloudDrive2OfflineResponse)
async def clouddrive2_offline_download(
    request: CloudDrive2OfflineRequest,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 添加离线下载任务
    
    兼容 CloudDrive2 的离线下载 API 格式，用于替换其他系统中的 CloudDrive2 服务地址。
    
    请求示例：
    ```json
    {
        "path": "/downloads",
        "url": "magnet:?xt=urn:btih:...",
        "type": "0"
    }
    ```
    
    响应示例：
    ```json
    {
        "success": true,
        "data": {
            "taskId": "abc123",
            "name": "filename"
        }
    }
    ```
    """
    try:
        provider = await get_provider(drive_id)
        
        # 将 path 转换为 save_cid（简化处理，使用默认路径）
        # 实际使用时可以通过 path 查找对应的 cid
        save_cid = None
        
        # 添加任务
        resp = await provider.offline_add_url(
            url=request.url,
            save_cid=save_cid
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
            
            logger.error(f"CloudDrive2 compat: Failed to add offline URL: {error_msg}")
            return CloudDrive2OfflineResponse(
                success=False,
                message=error_msg
            )
        
        # 返回 CloudDrive2 格式的响应
        return CloudDrive2OfflineResponse(
            success=True,
            data={
                "taskId": resp.get("info_hash", ""),
                "name": resp.get("name", request.name or ""),
                "url": request.url,
                "path": request.path
            },
            message="添加任务成功"
        )
    except HTTPException as e:
        return CloudDrive2OfflineResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CloudDrive2 compat: Error adding offline URL: {e}")
        return CloudDrive2OfflineResponse(
            success=False,
            message=f"添加任务失败: {str(e)}"
        )


@router.get("/cd2/tasks", response_model=CloudDrive2OfflineResponse)
async def clouddrive2_offline_list(
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 获取离线任务列表
    
    返回 CloudDrive2 格式的任务列表
    """
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_list(page=1, per_page=100)
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "获取任务列表失败")
            return CloudDrive2OfflineResponse(
                success=False,
                message=error_msg
            )
        
        # 转换任务格式
        tasks_data = resp.get("tasks", [])
        cd2_tasks = []
        for task in tasks_data:
            status_map = {
                0: "pending",
                1: "downloading", 
                2: "completed",
                -1: "failed"
            }
            cd2_tasks.append({
                "taskId": task.get("info_hash", ""),
                "name": task.get("name", ""),
                "size": task.get("size", 0),
                "status": status_map.get(task.get("status", 0), "unknown"),
                "progress": task.get("percent", 0),
                "speed": task.get("speed", 0),
                "createTime": task.get("create_time", 0),
                "url": task.get("url", "")
            })
        
        return CloudDrive2OfflineResponse(
            success=True,
            data={
                "tasks": cd2_tasks,
                "total": len(cd2_tasks)
            }
        )
    except HTTPException as e:
        return CloudDrive2OfflineResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CloudDrive2 compat: Error getting offline list: {e}")
        return CloudDrive2OfflineResponse(
            success=False,
            message=f"获取任务列表失败: {str(e)}"
        )


@router.delete("/cd2/tasks/{task_id}", response_model=CloudDrive2OfflineResponse)
async def clouddrive2_offline_delete(
    task_id: str,
    drive_id: Optional[str] = Query(None, description="网盘ID")
):
    """
    CloudDrive2 兼容接口 - 删除离线任务
    """
    try:
        provider = await get_provider(drive_id)
        
        resp = await provider.offline_remove([task_id])
        
        if not resp.get("state", False):
            error_msg = resp.get("error", "删除任务失败")
            return CloudDrive2OfflineResponse(
                success=False,
                message=error_msg
            )
        
        return CloudDrive2OfflineResponse(
            success=True,
            message="删除任务成功"
        )
    except HTTPException as e:
        return CloudDrive2OfflineResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"CloudDrive2 compat: Error removing offline task: {e}")
        return CloudDrive2OfflineResponse(
            success=False,
            message=f"删除任务失败: {str(e)}"
        )
