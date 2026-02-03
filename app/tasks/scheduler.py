"""
任务调度器

基于 apscheduler 的任务调度
"""
import logging
from typing import Dict, Optional
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.models.task import StrmTask, TaskStatus
from app.services.drive_service import DriveService
from app.services.strm_service import StrmService
from app.services.file_service import FileService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._running_tasks: Dict[str, str] = {}  # task_id -> job_id
    
    async def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("Task scheduler started")
        
        # 加载所有启用调度的任务
        try:
            tasks = await StrmTask.filter(schedule_enabled=True).all()
            for task in tasks:
                await self.add_task(task)
            logger.info(f"Loaded {len(tasks)} scheduled tasks")
        except Exception as e:
            logger.warning(f"Failed to load scheduled tasks: {e}")
    
    async def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("Task scheduler stopped")
    
    async def add_task(self, task: StrmTask) -> bool:
        """
        添加任务到调度器
        
        Args:
            task: STRM 任务
            
        Returns:
            是否成功
        """
        if not task.schedule_enabled:
            return False
        
        # 移除已存在的任务
        if task.id in self._running_tasks:
            await self.remove_task(task.id)
        
        # 构建触发器
        trigger = self._build_trigger(task)
        if not trigger:
            logger.warning(f"Failed to build trigger for task {task.id}")
            return False
        
        try:
            # 添加任务
            job = self.scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger,
                id=task.id,
                args=[task.id],
                replace_existing=True
            )
            
            self._running_tasks[task.id] = job.id
            
            logger.info(f"Added task {task.id} to scheduler")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to add task {task.id}: {e}")
            return False
    
    async def remove_task(self, task_id: str) -> bool:
        """
        从调度器移除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功
        """
        try:
            self.scheduler.remove_job(task_id)
            self._running_tasks.pop(task_id, None)
            logger.info(f"Removed task {task_id} from scheduler")
            return True
        except Exception:
            return False
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            self.scheduler.pause_job(task_id)
            return True
        except Exception:
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            self.scheduler.resume_job(task_id)
            return True
        except Exception:
            return False
    
    def _build_trigger(self, task: StrmTask) -> Optional[object]:
        """
        构建触发器
        
        Args:
            task: STRM 任务
            
        Returns:
            触发器对象
        """
        config = task.schedule_config or {}
        
        if task.schedule_type == "interval":
            # 间隔触发
            interval = config.get("interval", 3600)
            unit = config.get("unit", "seconds")
            
            kwargs = {}
            if unit == "seconds":
                kwargs["seconds"] = interval
            elif unit == "minutes":
                kwargs["minutes"] = interval
            elif unit == "hours":
                kwargs["hours"] = interval
            elif unit == "days":
                kwargs["days"] = interval
            
            return IntervalTrigger(**kwargs)
        
        elif task.schedule_type == "cron":
            # Cron 触发
            return CronTrigger(
                minute=config.get("minute", "0"),
                hour=config.get("hour", "*"),
                day=config.get("day", "*"),
                month=config.get("month", "*"),
                day_of_week=config.get("day_of_week", "*")
            )
        
        return None
    
    async def _execute_task_wrapper(self, task_id: str):
        """
        任务执行包装器
        
        由调度器调用
        """
        from .executor import execute_strm_task
        
        logger.info(f"Scheduler executing task: {task_id}")
        
        try:
            # 获取任务
            task = await StrmTask.filter(id=task_id).first()
            if not task:
                logger.error(f"Task not found: {task_id}")
                return
            
            # 检查任务是否已经在运行
            if task.status == TaskStatus.RUNNING:
                logger.warning(f"Task {task_id} is already running, skipping")
                return
            
            # 获取服务
            settings = get_settings()
            drive_service = DriveService(settings.data_dir)
            
            provider = await drive_service.get_provider(task.drive_id)
            file_service = FileService(provider)
            strm_service = StrmService(
                file_service=file_service,
                provider=provider,
                base_url=task.base_url
            )
            
            # 执行任务
            await execute_strm_task(task_id, strm_service)
            
        except Exception as e:
            logger.exception(f"Scheduled task execution failed: {e}")
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self.scheduler.running,
            "tasks_count": len(self._running_tasks),
            "active_tasks": list(self._running_tasks.keys())
        }


# 全局调度器实例
scheduler = TaskScheduler()
