"""
WebDAV 路由
提供 115 网盘的 WebDAV 访问接口
"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException

from app.models.drive import Drive
from app.providers.p115 import P115Provider
from app.providers.webdav import webdav_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webdav", tags=["webdav"])


async def get_provider_for_drive(drive_id: str):
    """获取指定网盘的 WebDAV 提供者"""
    drive = await Drive.get_or_none(id=drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    # 获取 P115 客户端
    p115_provider = P115Provider(drive.cookie_file)
    client = await p115_provider._get_client()

    return webdav_handler.get_provider(str(drive.id), client)


@router.api_route("/{drive_id}/{path:path}", methods=["OPTIONS"])
async def webdav_options(drive_id: str, path: str, request: Request):
    """WebDAV OPTIONS"""
    return await webdav_handler.handle_options(request)


@router.api_route("/{drive_id}/{path:path}", methods=["PROPFIND"])
async def webdav_propfind(drive_id: str, path: str, request: Request):
    """WebDAV PROPFIND - 获取资源属性"""
    logger.info(f"PROPFIND {drive_id}/{path}")

    provider = await get_provider_for_drive(drive_id)
    depth = request.headers.get("Depth", "0")

    # 规范化路径
    path = "/" + path.strip("/") if path else "/"

    return await webdav_handler.handle_propfind(provider, path, depth)


@router.api_route("/{drive_id}/{path:path}", methods=["GET", "HEAD"])
async def webdav_get(drive_id: str, path: str, request: Request):
    """WebDAV GET - 获取资源内容"""
    logger.info(f"GET {drive_id}/{path}")

    provider = await get_provider_for_drive(drive_id)

    # 规范化路径
    path = "/" + path.strip("/") if path else "/"

    return await webdav_handler.handle_get(provider, path)


@router.api_route("/{drive_id}", methods=["OPTIONS", "PROPFIND", "GET", "HEAD"])
async def webdav_root(drive_id: str, request: Request):
    """WebDAV 根目录"""
    method = request.method

    if method == "OPTIONS":
        return await webdav_handler.handle_options(request)

    provider = await get_provider_for_drive(drive_id)

    if method == "PROPFIND":
        depth = request.headers.get("Depth", "0")
        return await webdav_handler.handle_propfind(provider, "/", depth)

    return await webdav_handler.handle_get(provider, "/")
