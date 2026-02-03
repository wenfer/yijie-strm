"""
API 依赖注入模块
"""
from typing import Optional
from fastapi import Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.drive_service import DriveService
from app.services.task_service import TaskService


async def get_settings_dep() -> Settings:
    """获取配置依赖"""
    return get_settings()


async def get_drive_service(settings: Settings = get_settings_dep()) -> DriveService:
    """获取 DriveService 依赖"""
    return DriveService(settings.data_dir)


async def get_task_service() -> TaskService:
    """获取 TaskService 依赖"""
    return TaskService()
