"""
任务执行器

负责任务的实际执行
"""
import logging

from app.models.task import StrmTask
from app.services.strm_service import StrmService

logger = logging.getLogger(__name__)


async def execute_strm_task(
    task_id: str,
    strm_service: StrmService
) -> bool:
    """
    执行 STRM 生成任务
    
    Args:
        task_id: 任务 ID
        strm_service: StrmService 实例
        
    Returns:
        是否成功
    """
    logger.info(f"Executing STRM task: {task_id}")
    
    try:
        # 获取任务
        task = await StrmTask.filter(id=task_id).first()
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
        
        # 执行任务
        result = await strm_service.generate_strm_files(task)
        
        logger.info(
            f"Task {task_id} completed: "
            f"added={result.get('files_added', 0)}, "
            f"updated={result.get('files_updated', 0)}, "
            f"deleted={result.get('files_deleted', 0)}, "
            f"skipped={result.get('files_skipped', 0)}"
        )
        
        return True
        
    except Exception as e:
        logger.exception(f"Task execution failed: {e}")
        return False
