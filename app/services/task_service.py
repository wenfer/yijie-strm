"""
任务管理服务
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime

from app.models.task import StrmTask, StrmRecord, TaskLog, TaskStatus
from app.core.exceptions import TaskNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""
    
    async def create_task(
        self,
        name: str,
        drive_id: str,
        source_cid: str,
        output_dir: str,
        **kwargs
    ) -> StrmTask:
        """
        创建任务
        
        Args:
            name: 任务名称
            drive_id: 网盘 ID
            source_cid: 源文件夹 CID
            output_dir: 输出目录
            **kwargs: 其他配置
            
        Returns:
            StrmTask 对象
        """
        import time
        
        # 生成任务 ID
        task_id = f"task_{int(time.time() * 1000)}"
        
        # 验证必填参数
        if not name:
            raise ValidationError("任务名称不能为空")
        if not drive_id:
            raise ValidationError("网盘 ID 不能为空")
        if not source_cid:
            raise ValidationError("源文件夹 CID 不能为空")
        if not output_dir:
            raise ValidationError("输出目录不能为空")
        
        # 创建任务
        task = await StrmTask.create(
            id=task_id,
            name=name,
            drive_id=drive_id,
            source_cid=source_cid,
            output_dir=output_dir,
            base_url=kwargs.get("base_url"),
            include_video=kwargs.get("include_video", True),
            include_audio=kwargs.get("include_audio", False),
            custom_extensions=kwargs.get("custom_extensions"),
            schedule_enabled=kwargs.get("schedule_enabled", False),
            schedule_type=kwargs.get("schedule_type"),
            schedule_config=kwargs.get("schedule_config"),
            watch_enabled=kwargs.get("watch_enabled", False),
            watch_interval=kwargs.get("watch_interval", 1800),
            delete_orphans=kwargs.get("delete_orphans", True),
            preserve_structure=kwargs.get("preserve_structure", True),
            overwrite_strm=kwargs.get("overwrite_strm", False),
            status=TaskStatus.IDLE
        )
        
        logger.info(f"Created task: {task_id}")
        return task
    
    async def get_task(self, task_id: str) -> StrmTask:
        """
        获取任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            StrmTask 对象
        """
        task = await StrmTask.filter(id=task_id).first()
        if not task:
            raise TaskNotFoundError(task_id)
        return task
    
    async def list_tasks(
        self,
        drive_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[StrmTask]:
        """
        获取任务列表
        
        Args:
            drive_id: 可选的网盘 ID 过滤
            status: 可选的状态过滤
            
        Returns:
            任务列表
        """
        query = StrmTask.all()
        
        if drive_id:
            query = query.filter(drive_id=drive_id)
        
        if status:
            query = query.filter(status=status)
        
        return await query.order_by("-created_at")
    
    async def update_task(self, task_id: str, **updates) -> StrmTask:
        """
        更新任务
        
        Args:
            task_id: 任务 ID
            **updates: 更新字段
            
        Returns:
            StrmTask 对象
        """
        task = await self.get_task(task_id)
        
        # 允许更新的字段
        allowed_fields = {
            "name", "source_cid", "output_dir", "base_url",
            "include_video", "include_audio", "custom_extensions",
            "schedule_enabled", "schedule_type", "schedule_config",
            "watch_enabled", "watch_interval",
            "delete_orphans", "preserve_structure", "overwrite_strm"
        }
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(task, field, value)
        
        await task.save()
        logger.info(f"Updated task: {task_id}")
        return task
    
    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功
        """
        task = await self.get_task(task_id)
        
        # 关联的 STRM 记录会被级联删除
        await task.delete()
        
        logger.info(f"Deleted task: {task_id}")
        return True
    
    async def get_task_statistics(self, task_id: str) -> Dict:
        """
        获取任务统计信息
        
        Args:
            task_id: 任务 ID
            
        Returns:
            统计信息字典
        """
        task = await self.get_task(task_id)
        
        # 获取活跃记录数
        active_count = await StrmRecord.filter(
            task=task,
            status="active"
        ).count()
        
        # 获取最近日志
        recent_log = await TaskLog.filter(
            task=task
        ).order_by("-start_time").first()
        
        return {
            "task_id": task_id,
            "task_name": task.name,
            "status": task.status,
            "total_runs": task.total_runs,
            "total_files_generated": task.total_files_generated,
            "active_records": active_count,
            "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
            "last_run_status": task.last_run_status,
            "last_run_message": task.last_run_message,
            "recent_log": recent_log.to_dict() if recent_log else None
        }
    
    async def get_task_records(
        self,
        task_id: str,
        status: Optional[str] = "active"
    ) -> List[StrmRecord]:
        """
        获取任务的 STRM 记录
        
        Args:
            task_id: 任务 ID
            status: 状态过滤
            
        Returns:
            STRM 记录列表
        """
        task = await self.get_task(task_id)
        
        query = StrmRecord.filter(task=task)
        if status:
            query = query.filter(status=status)
        
        return await query.order_by("-created_at")
    
    async def get_task_logs(self, task_id: str, limit: int = 50) -> List[TaskLog]:
        """
        获取任务日志
        
        Args:
            task_id: 任务 ID
            limit: 最大返回数量
            
        Returns:
            日志列表
        """
        task = await self.get_task(task_id)
        
        return await TaskLog.filter(
            task=task
        ).order_by("-start_time").limit(limit)
    
    async def delete_task_record(
        self,
        task_id: str,
        record_id: str,
        delete_file: bool = True
    ) -> bool:
        """
        删除单个 STRM 记录
        
        Args:
            task_id: 任务 ID
            record_id: 记录 ID
            delete_file: 是否同时删除物理文件
            
        Returns:
            是否删除成功
        """
        from pathlib import Path
        
        task = await self.get_task(task_id)
        record = await StrmRecord.filter(id=record_id, task=task).first()
        
        if not record:
            raise TaskNotFoundError(f"记录不存在: {record_id}")
        
        # 删除物理文件
        if delete_file and record.strm_path:
            try:
                strm_file = Path(record.strm_path)
                if strm_file.exists():
                    strm_file.unlink()
                    logger.info(f"已删除 STRM 文件: {record.strm_path}")
            except Exception as e:
                logger.warning(f"删除文件失败: {record.strm_path}, 错误: {e}")
        
        # 删除数据库记录
        await record.delete()
        logger.info(f"已删除记录: {record_id}")
        
        return True
    
    async def delete_task_records(
        self,
        task_id: str,
        record_ids: Optional[List[str]] = None,
        delete_files: bool = True
    ) -> int:
        """
        批量删除 STRM 记录
        
        Args:
            task_id: 任务 ID
            record_ids: 记录 ID 列表，None 表示删除所有
            delete_files: 是否同时删除物理文件
            
        Returns:
            删除的记录数量
        """
        from pathlib import Path
        
        task = await self.get_task(task_id)
        
        # 构建查询
        query = StrmRecord.filter(task=task)
        if record_ids:
            query = query.filter(id__in=record_ids)
        
        records = await query.all()
        deleted_count = 0
        
        for record in records:
            # 删除物理文件
            if delete_files and record.strm_path:
                try:
                    strm_file = Path(record.strm_path)
                    if strm_file.exists():
                        strm_file.unlink()
                        logger.info(f"已删除 STRM 文件: {record.strm_path}")
                except Exception as e:
                    logger.warning(f"删除文件失败: {record.strm_path}, 错误: {e}")
            
            # 删除数据库记录
            await record.delete()
            deleted_count += 1
        
        logger.info(f"批量删除完成，共删除 {deleted_count} 条记录")
        return deleted_count
    
    async def should_include_file(
        self,
        task: StrmTask,
        filename: str
    ) -> bool:
        """
        判断文件是否应该被包含
        
        Args:
            task: 任务
            filename: 文件名
            
        Returns:
            是否应该包含
        """
        from pathlib import Path
        ext = Path(filename).suffix.lower()
        
        # 自定义扩展名优先
        if task.custom_extensions:
            return ext in [e.lower() if e.startswith('.') else f'.{e.lower()}'
                          for e in task.custom_extensions]
        
        # 默认过滤规则
        if task.include_video and ext in StrmTask.VIDEO_EXTENSIONS:
            return True
        
        if task.include_audio and ext in StrmTask.AUDIO_EXTENSIONS:
            return True
        
        return False
