"""
STRM 任务调度服务
"""
import time
import logging
import threading
import traceback
from typing import Dict, Optional
from datetime import datetime, timedelta

try:
    import schedule
except ImportError:
    schedule = None
    logging.warning("schedule library not installed. Install with: pip install schedule")

from .task_service import TaskService, StrmTask
from .event_monitor import EventMonitor, EventProcessor

logger = logging.getLogger(__name__)


class SchedulerService:
    """任务调度服务"""

    def __init__(self, task_service: TaskService, strm_service=None):
        self.task_service = task_service
        self.strm_service = strm_service
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running_tasks: Dict[str, threading.Thread] = {}
        self._watch_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

        # 事件监听器（每个 drive 一个）
        self._event_monitors: Dict[str, EventMonitor] = {}

        if schedule is None:
            logger.error("schedule library not available. Scheduler will not work.")

    def set_strm_service(self, strm_service):
        """设置 STRM 服务（用于延迟初始化）"""
        self.strm_service = strm_service
        logger.info("STRM service updated in scheduler")

    def start(self):
        """启动调度器"""
        if not schedule:
            logger.error("Cannot start scheduler: schedule library not installed")
            return False

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            logger.warning("Scheduler already running")
            return False

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()

        logger.info("Scheduler started")
        return True

    def stop(self):
        """停止调度器"""
        if not self._scheduler_thread or not self._scheduler_thread.is_alive():
            logger.warning("Scheduler not running")
            return False

        self._stop_event.set()

        # 停止所有监听线程
        for task_id in list(self._watch_threads.keys()):
            self.stop_watch(task_id)

        # 等待调度器线程结束
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

        logger.info("Scheduler stopped")
        return True

    def is_running(self) -> bool:
        """检查调度器是否运行"""
        return self._scheduler_thread is not None and self._scheduler_thread.is_alive()

    def schedule_task(self, task: StrmTask):
        """调度任务"""
        if not schedule:
            logger.error("Cannot schedule task: schedule library not installed")
            return

        if not task.schedule_enabled:
            return

        schedule_type = task.schedule_type
        schedule_config = task.schedule_config or {}

        try:
            if schedule_type == 'interval':
                # 间隔调度
                interval = schedule_config.get('interval', 3600)  # 默认 1 小时
                unit = schedule_config.get('unit', 'seconds')  # seconds/minutes/hours/days

                if unit == 'seconds':
                    schedule.every(interval).seconds.do(
                        self._execute_task_wrapper, task.task_id
                    ).tag(task.task_id)
                elif unit == 'minutes':
                    schedule.every(interval).minutes.do(
                        self._execute_task_wrapper, task.task_id
                    ).tag(task.task_id)
                elif unit == 'hours':
                    schedule.every(interval).hours.do(
                        self._execute_task_wrapper, task.task_id
                    ).tag(task.task_id)
                elif unit == 'days':
                    schedule.every(interval).days.do(
                        self._execute_task_wrapper, task.task_id
                    ).tag(task.task_id)

                logger.info(f"Scheduled task {task.task_id} to run every {interval} {unit}")

            elif schedule_type == 'cron':
                # Cron 风格调度
                time_str = schedule_config.get('time', '00:00')  # HH:MM
                schedule.every().day.at(time_str).do(
                    self._execute_task_wrapper, task.task_id
                ).tag(task.task_id)

                logger.info(f"Scheduled task {task.task_id} to run daily at {time_str}")

            # 启动文件监听
            if task.watch_enabled:
                self.start_watch(task)

        except Exception as e:
            logger.error(f"Failed to schedule task {task.task_id}: {e}")

    def unschedule_task(self, task_id: str):
        """取消调度任务"""
        if not schedule:
            return

        schedule.clear(task_id)
        self.stop_watch(task_id)
        logger.info(f"Unscheduled task: {task_id}")

    def reschedule_task(self, task: StrmTask):
        """重新调度任务"""
        self.unschedule_task(task.task_id)
        self.schedule_task(task)

    def run_task_now(self, task_id: str) -> bool:
        """立即执行任务"""
        with self._lock:
            if task_id in self._running_tasks:
                logger.warning(f"Task {task_id} is already running")
                return False

        # 在新线程中执行任务
        thread = threading.Thread(
            target=self._execute_task_wrapper,
            args=(task_id,),
            daemon=True
        )
        thread.start()

        return True

    def start_watch(self, task: StrmTask):
        """启动文件监听（基于事件 API）"""
        if not task.watch_enabled:
            return

        if task.task_id in self._watch_threads:
            logger.warning(f"Watch already started for task {task.task_id}")
            return

        # 获取或创建该 drive 的事件监听器
        if task.drive_id not in self._event_monitors:
            # 获取该 drive 的 client
            client = self.strm_service.drive_service.get_client(task.drive_id)
            if not client:
                logger.error(f"Cannot start watch for task {task.task_id}: client not found for drive {task.drive_id}")
                return

            self._event_monitors[task.drive_id] = EventMonitor(client, cooldown=0.2)

        event_monitor = self._event_monitors[task.drive_id]

        # 获取任务的最后事件 ID
        last_event_id = task.last_event_id or 0

        # 启动监听
        event_monitor.start_monitoring(
            task_id=task.task_id,
            source_cid=task.source_cid,
            callback=lambda events: self._on_events_detected(task.task_id, events),
            from_event_id=last_event_id
        )

        # 创建监听线程
        thread = threading.Thread(
            target=self._watch_loop_event_based,
            args=(task,),
            daemon=True
        )
        thread.start()

        self._watch_threads[task.task_id] = thread
        logger.info(f"Started event-based watch for task {task.task_id} (check interval: {task.watch_interval}s)")

    def stop_watch(self, task_id: str):
        """停止文件监听"""
        if task_id in self._watch_threads:
            # 从事件监听器中移除
            task = self.task_service.get_task(task_id)
            if task and task.drive_id in self._event_monitors:
                self._event_monitors[task.drive_id].stop_monitoring(task_id)

            # 线程会在下次循环时检查 _stop_event 并退出
            del self._watch_threads[task_id]
            logger.info(f"Stopped watch for task {task_id}")

    def _run_scheduler(self):
        """调度器主循环"""
        logger.info("Scheduler loop started")

        # 加载所有启用调度的任务
        tasks = self.task_service.list_tasks()
        for task in tasks:
            if task.schedule_enabled:
                self.schedule_task(task)

        # 主循环
        while not self._stop_event.is_set():
            try:
                if schedule:
                    schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)

        logger.info("Scheduler loop stopped")

    def _watch_loop_event_based(self, task: StrmTask):
        """基于事件 API 的文件监听循环"""
        logger.info(f"Event-based watch loop started for task {task.task_id}")

        last_check = 0

        while task.task_id in self._watch_threads and not self._stop_event.is_set():
            try:
                now = time.time()

                # 检查是否到达检查间隔
                if now - last_check >= task.watch_interval:
                    logger.debug(f"Checking events for task {task.task_id}")

                    # 检查新事件
                    if task.drive_id in self._event_monitors:
                        event_monitor = self._event_monitors[task.drive_id]
                        events = event_monitor.check_events(task.task_id, task.source_cid)

                        if events:
                            # 处理事件
                            changes = EventProcessor.process_events(events)
                            summary = EventProcessor.summarize_changes(changes)

                            logger.info(
                                f"Events detected for task {task.task_id}: {summary} "
                                f"({len(events)} events)"
                            )

                            # 更新任务的最后事件 ID
                            max_event_id = max(int(e['id']) for e in events)
                            self.task_service.update_task(task.task_id, {
                                'last_event_id': max_event_id
                            })

                            # 触发同步
                            self.run_task_now(task.task_id)

                    last_check = now

                # 短暂休眠
                time.sleep(10)

            except Exception as e:
                logger.error(f"Error in event-based watch loop for task {task.task_id}: {e}")
                logger.error(traceback.format_exc())
                time.sleep(60)

        logger.info(f"Event-based watch loop stopped for task {task.task_id}")

    def _on_events_detected(self, task_id: str, events: list):
        """事件检测回调"""
        try:
            changes = EventProcessor.process_events(events)
            summary = EventProcessor.summarize_changes(changes)

            logger.info(f"Events detected for task {task_id}: {summary}")

            # 触发同步
            self.run_task_now(task_id)

        except Exception as e:
            logger.error(f"Error processing events for task {task_id}: {e}")

    def _execute_task_wrapper(self, task_id: str):
        """任务执行包装器（防止并发）"""
        # 检查是否已在运行
        with self._lock:
            if task_id in self._running_tasks:
                logger.warning(f"Task {task_id} is already running, skipping")
                return

            # 标记为运行中
            self._running_tasks[task_id] = threading.current_thread()

        start_time = time.time()
        log_data = {
            'start_time': start_time,
            'status': 'error',
            'files_scanned': 0,
            'files_added': 0,
            'files_updated': 0,
            'files_deleted': 0,
            'files_skipped': 0
        }

        try:
            # 检查 strm_service 是否可用
            if not self.strm_service:
                # STRM service 未初始化，说明认证失败
                task = self.task_service.get_task(task_id)
                if task:
                    # 标记网盘为未认证状态
                    from .drive_service import DriveService
                    drive_service = DriveService()
                    drive_service.mark_drive_unauthenticated(task.drive_id)
                    drive_service.close()

                    error_msg = f"Token expired or invalid for drive {task.drive_id}. Please re-authenticate."
                    logger.error(f"Task {task_id} failed: {error_msg}")

                    # 更新任务状态
                    self.task_service.update_task_status(task_id, 'error', error_msg)

                    log_data.update({
                        'status': 'error',
                        'message': error_msg,
                        'error_trace': 'STRM service not initialized - authentication required'
                    })
                else:
                    raise RuntimeError("STRM service not initialized. Please authenticate first.")

                return

            # 更新任务状态
            self.task_service.update_task_status(task_id, 'running')

            # 执行任务
            logger.info(f"Executing task: {task_id}")
            result = self.strm_service.execute_task(task_id)

            # 检查是否是 token 错误
            if not result.get('success') and result.get('token_error'):
                # Token 错误，更新任务状态并记录
                log_data.update({
                    'status': 'error',
                    'message': result.get('message', 'Token expired or invalid'),
                    'error_trace': 'Token authentication failed'
                })
                self.task_service.update_task_status(
                    task_id,
                    'error',
                    result.get('message', 'Token expired or invalid')
                )
                logger.error(f"Task {task_id} failed due to token error: {result.get('message')}")
            else:
                # 更新日志数据
                log_data.update({
                    'status': 'success' if result.get('success') else 'error',
                    'message': result.get('message', ''),
                    'files_scanned': result.get('files_scanned', 0),
                    'files_added': result.get('files_added', 0),
                    'files_updated': result.get('files_updated', 0),
                    'files_deleted': result.get('files_deleted', 0),
                    'files_skipped': result.get('files_skipped', 0)
                })

                # 更新任务状态
                if result.get('success'):
                    self.task_service.update_task_status(task_id, 'idle', 'Task completed successfully')
                    # 更新统计
                    task = self.task_service.get_task(task_id)
                    if task:
                        self.task_service.update_task(task_id, {
                            'total_runs': task.total_runs + 1,
                            'total_files_generated': task.total_files_generated + result.get('files_added', 0)
                        })
                else:
                    self.task_service.update_task_status(task_id, 'error', result.get('message', 'Unknown error'))

            logger.info(f"Task {task_id} completed: {result}")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Task {task_id} failed: {e}\n{error_trace}")

            # 检查是否是认证相关错误
            error_msg = str(e).lower()
            if 'token' in error_msg or 'auth' in error_msg or 'unauthorized' in error_msg or '401' in error_msg:
                task = self.task_service.get_task(task_id)
                if task:
                    # 标记网盘为未认证状态
                    from .drive_service import DriveService
                    drive_service = DriveService()
                    drive_service.mark_drive_unauthenticated(task.drive_id)
                    drive_service.close()
                    logger.error(f"Token error detected for drive {task.drive_id}, marked as unauthenticated")

            log_data.update({
                'status': 'error',
                'message': str(e),
                'error_trace': error_trace
            })

            # 更新任务状态
            self.task_service.update_task_status(task_id, 'error', str(e))

        finally:
            # 记录执行时间
            end_time = time.time()
            log_data['end_time'] = end_time
            log_data['duration'] = end_time - start_time

            # 添加任务日志
            self.task_service.add_task_log(task_id, log_data)

            # 移除运行标记
            with self._lock:
                self._running_tasks.pop(task_id, None)

    def get_scheduler_status(self) -> Dict:
        """获取调度器状态"""
        return {
            'running': self.is_running(),
            'scheduled_tasks': len(schedule.jobs) if schedule else 0,
            'running_tasks': len(self._running_tasks),
            'watch_tasks': len(self._watch_threads)
        }

    def reload_tasks(self):
        """重新加载所有任务"""
        if not schedule:
            return

        # 清除所有现有调度
        schedule.clear()

        # 停止所有监听
        for task_id in list(self._watch_threads.keys()):
            self.stop_watch(task_id)

        # 重新加载任务
        tasks = self.task_service.list_tasks()
        for task in tasks:
            if task.schedule_enabled:
                self.schedule_task(task)

        logger.info(f"Reloaded {len(tasks)} tasks")
