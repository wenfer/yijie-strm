"""
流媒体服务 API 路由

提供 302 重定向服务
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse

from app.services.drive_service import DriveService
from app.services.strm_service import StrmService
from app.services.file_service import FileService
from app.core.exceptions import DriveNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["流媒体服务"])


def get_drive_service() -> DriveService:
    """获取 DriveService 实例"""
    from app.core.config import get_settings
    settings = get_settings()
    return DriveService(settings.data_dir)


async def get_strm_service(
        drive_id: Optional[str] = None,
        drive_service: DriveService = Depends(get_drive_service)
) -> StrmService:
    """获取 StrmService 实例"""
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
        # 如果认证失效，自动重置认证状态
        try:
            await drive_service.reset_auth(drive_id)
            logger.info(f"Drive {drive_id} authentication expired, reset auth status")
        except Exception as e:
            logger.error(f"Failed to reset auth for drive {drive_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="网盘未认证或认证已过期，请重新扫码登录"
        )

    file_service = FileService(provider)

    return StrmService(
        file_service=file_service,
        provider=provider
    )


@router.get("/stream/{pick_code}")
async def stream_redirect(
        pick_code: str,
        request: Request,
        id: int = 0,
        drive_id: Optional[str] = None,
        strm_service: StrmService = Depends(get_strm_service)
):
    """
    流媒体 302 重定向
    
    根据 pick_code 获取下载链接并重定向
    """
    try:
        # 获取 User-Agent
        user_agent = request.headers.get("user-agent")

        # 获取下载链接
        url = await strm_service.get_stream_url(pick_code, id, user_agent)

        if not url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件不存在或无法获取下载链接: {pick_code}"
            )

        # 302 重定向
        return RedirectResponse(url=url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting stream URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取下载链接失败: {str(e)}"
        )


@router.get("/download/{pick_code}")
async def get_download_url_path(
        pick_code: str,
        request: Request,
        drive_id: Optional[str] = None,
        strm_service: StrmService = Depends(get_strm_service)
):
    """
    获取下载链接（API 接口，不返回 302）- 路径参数版本
    """
    return await _get_download_url_impl(pick_code, request, strm_service)


@router.get("/api/download")
async def get_download_url_query(
        pick_code: str,
        request: Request,
        drive_id: Optional[str] = None,
        strm_service: StrmService = Depends(get_strm_service)
):
    """
    获取下载链接（API 接口，不返回 302）- 查询参数版本（兼容前端）
    """
    return await _get_download_url_impl(pick_code, request, strm_service)


async def _get_download_url_impl(
        pick_code: str,
        request: Request,
        strm_service: StrmService
):
    """获取下载链接的实现"""
    try:
        # 获取 User-Agent
        user_agent = request.headers.get("user-agent")

        # 获取下载链接
        url = await strm_service.get_stream_url(pick_code)

        if not url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件不存在或无法获取下载链接: {pick_code}"
            )

        return {
            "success": True,
            "pick_code": pick_code,
            "url": url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取下载链接失败: {str(e)}"
        )
