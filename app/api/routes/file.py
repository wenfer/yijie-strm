"""
文件操作 API 路由
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel

from app.api.schemas import (
    FileItem as FileItemSchema, DataResponse, ResponseBase
)
from app.services.drive_service import DriveService
from app.services.file_service import FileService
from app.core.exceptions import DriveNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["文件操作"])

# 用于兼容旧版 API 的 router（无前缀）
compat_router = APIRouter(tags=["文件操作"])


# 兼容前端的文件列表响应
class FileListResponse(BaseModel):
    cid: str
    total: int
    offset: int
    limit: int
    items: List[FileItemSchema]


def get_drive_service() -> DriveService:
    """获取 DriveService 实例"""
    from app.core.config import get_settings
    settings = get_settings()
    return DriveService(settings.data_dir)


async def get_file_service(
    drive_id: Optional[str] = Query(None, description="网盘 ID"),
    drive_service: DriveService = Depends(get_drive_service)
) -> FileService:
    """获取 FileService 实例"""
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
            detail="网盘未认证或认证已过期"
        )
    
    return FileService(provider)


async def _list_files_impl(
    cid: str = "0",
    limit: int = 100,
    offset: int = 0,
    drive_id: Optional[str] = None,
    file_service: FileService = None
):
    """获取文件列表的实现"""
    try:
        files, total = await file_service.list_files(cid, limit, offset)
        return FileListResponse(
            cid=cid,
            items=[
                FileItemSchema(
                    id=f.id,
                    name=f.name,
                    is_dir=f.is_dir,
                    size=f.size,
                    parent_id=f.parent_id,
                    pick_code=f.pick_code,
                    sha1=f.sha1
                )
                for f in files
            ],
            total=total,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.exception(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件列表失败: {str(e)}"
        )


@router.get("/list")
async def list_files(
    cid: str = "0",
    limit: int = 100,
    offset: int = 0,
    drive_id: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """获取文件列表"""
    return await _list_files_impl(cid, limit, offset, drive_id, file_service)


async def _search_files_impl(
    keyword: str,
    cid: str = "0",
    limit: int = 100,
    offset: int = 0,
    file_service: FileService = None
):
    """搜索文件的实现"""
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索关键词不能为空"
        )
    
    try:
        files = await file_service.search_files(keyword, cid, limit)
        return FileListResponse(
            cid=cid,
            items=[
                FileItemSchema(
                    id=f.id,
                    name=f.name,
                    is_dir=f.is_dir,
                    size=f.size,
                    parent_id=f.parent_id,
                    pick_code=f.pick_code,
                    sha1=f.sha1
                )
                for f in files
            ],
            total=len(files),
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.exception(f"Error searching files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索文件失败: {str(e)}"
        )


@router.get("/search")
async def search_files(
    keyword: str,
    cid: str = "0",
    limit: int = 100,
    offset: int = 0,
    drive_id: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """搜索文件"""
    return await _search_files_impl(keyword, cid, limit, offset, file_service)


@router.get("/info/{file_id}", response_model=DataResponse)
async def get_file_info(
    file_id: str,
    drive_id: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """获取文件信息"""
    try:
        info = await file_service.get_file_info(file_id)
        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件不存在: {file_id}"
            )
        
        return DataResponse(data=FileItemSchema(
            id=info.id,
            name=info.name,
            is_dir=info.is_dir,
            size=info.size,
            parent_id=info.parent_id,
            pick_code=info.pick_code,
            sha1=info.sha1
        ))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting file info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件信息失败: {str(e)}"
        )


@router.get("/tree", response_model=DataResponse)
async def get_folder_tree(
    cid: str = "0",
    max_depth: int = 3,
    drive_id: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """获取目录树结构"""
    try:
        tree = await file_service.get_folder_tree(cid, max_depth)
        return DataResponse(data=tree)
    except Exception as e:
        logger.exception(f"Error getting folder tree: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取目录树失败: {str(e)}"
        )

# ========== 兼容旧版 API 路由（无前缀 /api/files） ==========

@compat_router.get("/list")
async def list_files_compat(
    cid: str = "0",
    limit: int = 100,
    offset: int = 0,
    drive_id: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """获取文件列表（兼容旧版 API）"""
    return await _list_files_impl(cid, limit, offset, drive_id, file_service)


@compat_router.get("/search")
async def search_files_compat(
    keyword: str,
    cid: str = "0",
    limit: int = 100,
    offset: int = 0,
    drive_id: Optional[str] = None,
    file_service: FileService = Depends(get_file_service)
):
    """搜索文件（兼容旧版 API）"""
    return await _search_files_impl(keyword, cid, limit, offset, file_service)
