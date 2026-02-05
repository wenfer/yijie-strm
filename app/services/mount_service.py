import multiprocessing
import os
import sys
import signal
import logging
import platform
import time
import threading
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.models.mount import Mount
from app.providers.fuse_ops import P115FuseOperations, HAS_FUSE, FUSE

logger = logging.getLogger(__name__)


@dataclass
class MountLogEntry:
    """挂载日志条目"""
    timestamp: str
    level: str  # INFO, ERROR, WARNING, DEBUG
    message: str


@dataclass
class MountSession:
    """挂载会话信息"""
    mount_id: str
    process: multiprocessing.Process
    message_queue: multiprocessing.Queue
    logs: List[MountLogEntry] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "starting"  # starting, running, failed, stopped
    error_message: Optional[str] = None
    _log_callbacks: List[Callable] = field(default_factory=list)
    _stop_event: threading.Event = field(default_factory=threading.Event)

    def add_log(self, level: str, message: str):
        """添加日志并通知回调"""
        entry = MountLogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message
        )
        self.logs.append(entry)
        # 保留最近 1000 条日志
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
        # 通知回调
        for callback in self._log_callbacks:
            try:
                callback(entry)
            except Exception:
                pass

    def on_log(self, callback: Callable):
        """注册日志回调"""
        self._log_callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """移除日志回调"""
        if callback in self._log_callbacks:
            self._log_callbacks.remove(callback)


def run_fuse_process(cookie_file: str, mount_point: str, config: dict, message_queue: multiprocessing.Queue):
    """
    FUSE 进程入口函数
    使用 message_queue 与父进程通信
    """
    def send_log(level: str, message: str):
        message_queue.put({"type": "log", "level": level, "message": message})

    if not HAS_FUSE:
        send_log("ERROR", "FUSE library not found. Cannot start mount.")
        message_queue.put({"type": "status", "status": "failed", "error": "FUSE library not found"})
        return

    try:
        # 配置日志
        logging.basicConfig(level=logging.INFO)

        # 确保挂载点存在
        send_log("INFO", f"Creating mount point: {mount_point}")
        os.makedirs(mount_point, exist_ok=True)

        # 实例化 Operations
        root_cid = config.get('root_cid', "0")
        send_log("INFO", f"Initializing FUSE operations with root_cid={root_cid}")

        try:
            ops = P115FuseOperations(cookie_file, mount_point, root_cid=root_cid)
            send_log("INFO", "FUSE operations initialized successfully")
        except Exception as e:
            send_log("ERROR", f"Failed to initialize FUSE operations: {e}")
            import traceback
            tb = traceback.format_exc()
            for line in tb.split('\n'):
                if line.strip():
                    send_log("ERROR", line)
            message_queue.put({"type": "status", "status": "failed", "error": str(e)})
            return

        # 启动 FUSE
        allow_other = config.get('allow_other', False)
        fs_args = {'foreground': True, 'allow_other': allow_other}

        if platform.system() == 'Darwin':
            fs_args['nothreads'] = True  # macOS 上可能需要

        send_log("INFO", f"Starting FUSE on {mount_point} (PID: {os.getpid()})")
        message_queue.put({"type": "status", "status": "running"})

        # 启动 FUSE (这会阻塞)
        FUSE(ops, mount_point, **fs_args)

        # FUSE 正常退出
        send_log("INFO", "FUSE process exited normally")
        message_queue.put({"type": "status", "status": "stopped"})

    except Exception as e:
        error_msg = f"FUSE process failed: {e}"
        send_log("ERROR", error_msg)
        import traceback
        tb = traceback.format_exc()
        for line in tb.split('\n'):
            if line.strip():
                send_log("ERROR", line)
        message_queue.put({"type": "status", "status": "failed", "error": str(e)})
        sys.exit(1)

class MountService:
    def __init__(self):
        # mount_id -> MountSession
        self._sessions: Dict[str, MountSession] = {}
        # 日志收集线程
        self._log_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._start_log_collector()

    def _start_log_collector(self):
        """启动日志收集线程"""
        def collector():
            while not self._stop_event.is_set():
                for mount_id, session in list(self._sessions.items()):
                    try:
                        # 非阻塞获取消息
                        while not session._stop_event.is_set():
                            try:
                                msg = session.message_queue.get(timeout=0.1)
                                if msg.get("type") == "log":
                                    session.add_log(msg.get("level", "INFO"), msg.get("message", ""))
                                elif msg.get("type") == "status":
                                    session.status = msg.get("status", "unknown")
                                    if msg.get("status") == "failed":
                                        session.error_message = msg.get("error")
                                        session.end_time = datetime.now()
                                    elif msg.get("status") == "running":
                                        session.start_time = datetime.now()
                                    elif msg.get("status") == "stopped":
                                        session.end_time = datetime.now()
                            except Exception:
                                break
                    except Exception as e:
                        logger.error(f"Error collecting logs for {mount_id}: {e}")

                time.sleep(0.1)

        self._log_thread = threading.Thread(target=collector, daemon=True)
        self._log_thread.start()

    def get_session(self, mount_id: str) -> Optional[MountSession]:
        """获取挂载会话"""
        return self._sessions.get(mount_id)

    def get_logs(self, mount_id: str, limit: int = 100) -> List[MountLogEntry]:
        """获取挂载日志"""
        session = self._sessions.get(mount_id)
        if session:
            return session.logs[-limit:]
        return []

    async def start_mount(self, mount: Mount, timeout: float = 10.0) -> dict:
        """启动挂载

        Args:
            mount: 挂载配置
            timeout: 等待启动结果的超时时间（秒）

        Returns:
            dict: 包含 success, message, logs 等信息的字典
        """
        mount_id = str(mount.id)
        logger.info(f"[start_mount] Starting mount process for mount_id={mount_id}")

        # 检查是否已有运行中的会话
        if mount_id in self._sessions:
            session = self._sessions[mount_id]
            if session.process and session.process.is_alive() and session.status == "running":
                logger.info(f"[start_mount] Mount {mount_id} already running")
                return {"success": True, "message": "Mount already running", "logs": [log.__dict__ for log in session.logs]}
            # 清理旧的会话
            logger.info(f"[start_mount] Cleaning up old session for {mount_id}")
            self._cleanup_session(mount_id)

        # 获取网盘信息
        logger.info(f"[start_mount] Fetching drive info for mount {mount_id}")
        await mount.fetch_related('drive')
        if not mount.drive:
            logger.error(f"[start_mount] Drive not found for mount {mount_id}")
            return {"success": False, "message": "Drive not found", "logs": []}

        cookie_file = str(mount.drive.cookie_file)
        mount_point = os.path.expanduser(mount.mount_point)
        logger.info(f"[start_mount] cookie_file={cookie_file}, mount_point={mount_point}")

        # 检查 cookie 文件是否存在
        if not os.path.exists(cookie_file):
            error_msg = f"Cookie file not found: {cookie_file}"
            logger.error(f"[start_mount] {error_msg}")
            return {"success": False, "message": error_msg, "logs": []}

        # 检查 FUSE 是否可用
        if not HAS_FUSE:
            error_msg = "FUSE library not available"
            logger.error(f"[start_mount] {error_msg}")
            return {"success": False, "message": error_msg, "logs": []}

        # 创建消息队列和会话
        logger.info(f"[start_mount] Creating message queue and session for {mount_id}")
        message_queue = multiprocessing.Queue()
        session = MountSession(
            mount_id=mount_id,
            process=None,  # 稍后设置
            message_queue=message_queue
        )
        self._sessions[mount_id] = session

        # 启动进程
        logger.info(f"[start_mount] Starting FUSE process for {mount_id}")
        p = multiprocessing.Process(
            target=run_fuse_process,
            args=(cookie_file, mount_point, mount.mount_config or {}, message_queue)
        )
        p.start()
        session.process = p
        logger.info(f"[start_mount] FUSE process started with PID {p.pid}")

        # 等待启动结果
        logger.info(f"[start_mount] Waiting for startup result (timeout={timeout}s)")
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 处理消息队列
            try:
                while True:
                    msg = message_queue.get_nowait()
                    logger.debug(f"[start_mount] Received message: {msg}")
                    if msg.get("type") == "log":
                        session.add_log(msg.get("level", "INFO"), msg.get("message", ""))
                    elif msg.get("type") == "status":
                        status = msg.get("status")
                        session.status = status
                        logger.info(f"[start_mount] Status changed to: {status}")

                        if status == "running":
                            # 启动成功
                            session.start_time = datetime.now()
                            mount.is_mounted = True
                            mount.pid = p.pid
                            await mount.save()
                            logger.info(f"[start_mount] Mount {mount_id} started successfully with PID {p.pid}")
                            return {
                                "success": True,
                                "message": f"Mount started with PID {p.pid}",
                                "pid": p.pid,
                                "logs": [log.__dict__ for log in session.logs]
                            }
                        elif status == "failed":
                            # 启动失败
                            session.error_message = msg.get("error")
                            session.end_time = datetime.now()
                            mount.is_mounted = False
                            mount.pid = None
                            await mount.save()
                            logger.error(f"[start_mount] Mount {mount_id} failed: {session.error_message}")
                            # 清理失败的进程
                            self._cleanup_session(mount_id)
                            return {
                                "success": False,
                                "message": f"Mount failed: {session.error_message}",
                                "error": session.error_message,
                                "logs": [log.__dict__ for log in session.logs]
                            }
            except Exception:
                pass

            # 检查进程是否还在运行
            if not p.is_alive():
                # 进程意外退出
                logger.error(f"[start_mount] Process exited unexpectedly for mount {mount_id}, exit_code={p.exitcode}")
                session.status = "failed"
                session.error_message = f"Process exited unexpectedly (exit_code={p.exitcode})"
                session.end_time = datetime.now()
                mount.is_mounted = False
                mount.pid = None
                await mount.save()
                return {
                    "success": False,
                    "message": "Mount process exited unexpectedly",
                    "error": session.error_message,
                    "logs": [log.__dict__ for log in session.logs]
                }

            time.sleep(0.1)

        # 超时了，但进程可能还在启动中
        # 返回当前状态，让前端继续轮询
        logger.warning(f"[start_mount] Timeout waiting for mount {mount_id}, but process is still running")
        mount.is_mounted = True
        mount.pid = p.pid
        await mount.save()
        return {
            "success": True,
            "message": f"Mount starting with PID {p.pid} (timeout waiting for confirmation)",
            "pid": p.pid,
            "logs": [log.__dict__ for log in session.logs],
            "pending": True
        }

    def _cleanup_session(self, mount_id: str):
        """清理挂载会话"""
        session = self._sessions.get(mount_id)
        if session:
            session._stop_event.set()
            if session.process and session.process.is_alive():
                session.process.terminate()
                session.process.join(timeout=2)
                if session.process.is_alive():
                    session.process.kill()
            if mount_id in self._sessions:
                del self._sessions[mount_id]

    async def stop_mount(self, mount: Mount) -> dict:
        """停止挂载"""
        mount_id = str(mount.id)
        mount_point = os.path.expanduser(mount.mount_point)

        logger.info(f"Stopping mount {mount_id} on {mount_point}")

        logs = []
        session = self._sessions.get(mount_id)
        if session:
            logs = [log.__dict__ for log in session.logs]

        # 1. 尝试系统卸载命令
        if sys.platform == 'darwin':
            # MacOS
            cmd = f"umount '{mount_point}'"
        else:
            # Linux
            cmd = f"fusermount -u '{mount_point}'"

        ret = os.system(cmd)
        if ret != 0:
            # 如果失败，尝试强制卸载
            if sys.platform == 'darwin':
                os.system(f"umount -f '{mount_point}'")
            else:
                os.system(f"fusermount -uz '{mount_point}'")

        # 2. 停止进程
        self._cleanup_session(mount_id)

        # 3. 清理残留进程 (如果根据 PID)
        if mount.pid:
            try:
                os.kill(mount.pid, signal.SIGTERM)
            except OSError:
                pass

        # 更新状态
        mount.is_mounted = False
        mount.pid = None
        await mount.save()

        return {"success": True, "message": "Mount stopped", "logs": logs}

    async def restore_mounts(self):
        """恢复之前的挂载（服务启动时调用）"""
        # 查找所有标记为已挂载的记录
        mounts = await Mount.filter(is_mounted=True).all()
        for mount in mounts:
            logger.info(f"Restoring mount {mount.id}")
            # 先重置状态，防止残留
            mount.is_mounted = False
            await mount.save()

            # 重新启动
            result = await self.start_mount(mount)
            if not result.get("success"):
                logger.error(f"Failed to restore mount {mount.id}: {result.get('message')}")

    async def get_mount_status(self, mount: Mount) -> dict:
        """检查挂载状态"""
        mount_id = str(mount.id)

        session = self._sessions.get(mount_id)
        if session:
            is_alive = session.process and session.process.is_alive()
            if is_alive and session.status in ("running", "starting"):
                return {
                    "is_mounted": True,
                    "status": session.status,
                    "pid": session.process.pid if session.process else None,
                    "logs": [log.__dict__ for log in session.logs[-50:]]
                }
            else:
                # 进程已死或已停止，清理
                if not is_alive and mount.is_mounted:
                    mount.is_mounted = False
                    await mount.save()
                return {
                    "is_mounted": False,
                    "status": session.status,
                    "error": session.error_message,
                    "logs": [log.__dict__ for log in session.logs]
                }

        # 检查 PID (遗留的挂载)
        if mount.pid:
            try:
                os.kill(mount.pid, 0)
                return {
                    "is_mounted": True,
                    "status": "running",
                    "pid": mount.pid,
                    "logs": []
                }
            except OSError:
                if mount.is_mounted:
                    mount.is_mounted = False
                    await mount.save()
                return {
                    "is_mounted": False,
                    "status": "stopped",
                    "logs": []
                }

        return {
            "is_mounted": False,
            "status": "stopped",
            "logs": []
        }

    async def get_mount_logs(self, mount_id: str, limit: int = 100) -> list:
        """获取挂载日志"""
        session = self._sessions.get(mount_id)
        if session:
            return [log.__dict__ for log in session.logs[-limit:]]
        return []

mount_service = MountService()
