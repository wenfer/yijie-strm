"""
网盘管理服务
"""
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.models.drive import Drive
from app.providers.p115 import P115Provider, provider_manager
from app.core.exceptions import DriveNotFoundError, ConflictError

logger = logging.getLogger(__name__)


class DriveService:
    """网盘管理服务"""
    
    def __init__(self, data_dir: Path):
        """
        初始化服务
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cookie_path(self, drive_id: str) -> str:
        """获取 Cookie 文件路径"""
        return str(self.data_dir / f"{drive_id}.txt")
    
    async def create_drive(self, name: str, drive_type: str = "115") -> Drive:
        """
        创建网盘
        
        Args:
            name: 网盘名称
            drive_type: 网盘类型
            
        Returns:
            Drive 对象
        """
        # 生成网盘 ID
        import time
        drive_id = f"{drive_type}_{int(time.time() * 1000)}"
        
        # 检查是否已存在同名网盘
        existing = await Drive.filter(name=name).first()
        if existing:
            raise ConflictError(f"网盘名称已存在: {name}")
        
        # 取消其他网盘的当前状态
        await Drive.filter(is_current=True).update(is_current=False)
        
        # 创建网盘
        drive = await Drive.create(
            id=drive_id,
            name=name,
            drive_type=drive_type,
            cookie_file=self._get_cookie_path(drive_id),
            is_current=True
        )
        
        logger.info(f"Created drive: {drive_id}")
        return drive
    
    async def get_drive(self, drive_id: str) -> Drive:
        """
        获取网盘
        
        Args:
            drive_id: 网盘 ID
            
        Returns:
            Drive 对象
        """
        drive = await Drive.filter(id=drive_id).first()
        if not drive:
            raise DriveNotFoundError(drive_id)
        return drive
    
    async def get_current_drive(self) -> Optional[Drive]:
        """获取当前默认网盘"""
        return await Drive.filter(is_current=True).first()
    
    async def list_drives(self) -> List[Drive]:
        """获取所有网盘列表"""
        return await Drive.all().order_by("-created_at")
    
    async def update_drive(self, drive_id: str, name: Optional[str] = None) -> Drive:
        """
        更新网盘信息
        
        Args:
            drive_id: 网盘 ID
            name: 新名称
            
        Returns:
            Drive 对象
        """
        drive = await self.get_drive(drive_id)
        
        if name:
            # 检查名称是否冲突
            existing = await Drive.filter(name=name).exclude(id=drive_id).first()
            if existing:
                raise ConflictError(f"网盘名称已存在: {name}")
            drive.name = name
        
        await drive.save()
        logger.info(f"Updated drive: {drive_id}")
        return drive
    
    async def set_current_drive(self, drive_id: str) -> Drive:
        """
        设置当前默认网盘
        
        Args:
            drive_id: 网盘 ID
            
        Returns:
            Drive 对象
        """
        # 取消其他网盘的当前状态
        await Drive.filter(is_current=True).update(is_current=False)
        
        # 设置新的当前网盘
        drive = await self.get_drive(drive_id)
        drive.is_current = True
        await drive.save()
        
        logger.info(f"Set current drive: {drive_id}")
        return drive
    
    async def delete_drive(self, drive_id: str) -> bool:
        """
        删除网盘
        
        Args:
            drive_id: 网盘 ID
            
        Returns:
            是否成功
        """
        drive = await self.get_drive(drive_id)
        
        # 关闭并移除 Provider
        await provider_manager.remove_provider(drive_id)
        
        # 删除 Cookie 文件
        if drive.cookie_file:
            cookie_path = Path(drive.cookie_file)
            if cookie_path.exists():
                cookie_path.unlink()
        
        # 删除数据库记录
        await drive.delete()
        
        logger.info(f"Deleted drive: {drive_id}")
        return True
    
    async def get_provider(self, drive_id: str) -> P115Provider:
        """
        获取网盘对应的 Provider
        
        Args:
            drive_id: 网盘 ID
            
        Returns:
            P115Provider 实例
        """
        drive = await self.get_drive(drive_id)
        
        if not drive.cookie_file:
            raise DriveNotFoundError(f"网盘未配置 Cookie 文件: {drive_id}")
        
        return await provider_manager.get_provider(drive_id, drive.cookie_file)
    
    async def check_authenticated(self, drive_id: str) -> bool:
        """
        检查网盘是否已认证
        
        Args:
            drive_id: 网盘 ID
            
        Returns:
            是否已认证
        """
        try:
            provider = await self.get_provider(drive_id)
            return await provider.is_authenticated()
        except Exception as e:
            logger.warning(f"Failed to check authentication: {e}")
            return False
