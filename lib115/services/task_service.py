"""
STRM 任务管理服务
"""
import os
import time
import json
import hashlib
import logging
import traceback
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from ..db.base import DatabaseInterface

logger = logging.getLogger(__name__)


@dataclass
class StrmTask:
    """STRM 任务模型"""
    task_id: str
    task_name: str
    drive_id: str
    source_cid: str
    output_dir: str
    base_url: Optional[str] = None

    # 文件过滤配置
    include_video: bool = True
    include_audio: bool = False
    custom_extensions: Optional[List[str]] = None

    # 调度配置
    schedule_enabled: bool = False
    schedule_type: Optional[str] = None  # interval/cron/manual
    schedule_config: Optional[Dict] = None

    # 监听配置
    watch_enabled: bool = False
    watch_interval: int = 3600

    # 同步选项
    delete_orphans: bool = True
    preserve_structure: bool = True

    # 状态信息
    status: str = 'idle'
    last_run_time: Optional[float] = None
    last_run_status: Optional[str] = None
    last_run_message: Optional[str] = None
    next_run_time: Optional[float] = None

    # 统计信息
    total_runs: int = 0
    total_files_generated: int = 0

    # 进度信息
    total_files: int = 0
    current_file_index: int = 0

    # 事件监听
    last_event_id: int = 0

    created_at: float = 0
    updated_at: float = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        # 转换列表和字典为 JSON 字符串
        if self.custom_extensions:
            data['custom_extensions'] = json.dumps(self.custom_extensions)
        else:
            data['custom_extensions'] = None

        if self.schedule_config:
            data['schedule_config'] = json.dumps(self.schedule_config)
        else:
            data['schedule_config'] = None

        # 转换布尔值为整数（SQLite 兼容）
        data['include_video'] = 1 if self.include_video else 0
        data['include_audio'] = 1 if self.include_audio else 0
        data['schedule_enabled'] = 1 if self.schedule_enabled else 0
        data['watch_enabled'] = 1 if self.watch_enabled else 0
        data['delete_orphans'] = 1 if self.delete_orphans else 0
        data['preserve_structure'] = 1 if self.preserve_structure else 0

        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'StrmTask':
        """从字典创建"""
        # 解析 JSON 字符串
        if data.get('custom_extensions'):
            data['custom_extensions'] = json.loads(data['custom_extensions'])

        if data.get('schedule_config'):
            data['schedule_config'] = json.loads(data['schedule_config'])

        # 转换整数为布尔值
        data['include_video'] = bool(data.get('include_video', 1))
        data['include_audio'] = bool(data.get('include_audio', 0))
        data['schedule_enabled'] = bool(data.get('schedule_enabled', 0))
        data['watch_enabled'] = bool(data.get('watch_enabled', 0))
        data['delete_orphans'] = bool(data.get('delete_orphans', 1))
        data['preserve_structure'] = bool(data.get('preserve_structure', 1))

        return cls(**data)


class TaskService:
    """任务管理服务"""

    # 默认视频扩展名
    VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.m2ts', '.rmvb'
    }

    # 默认音频扩展名
    AUDIO_EXTENSIONS = {
        '.mp3', '.flac', '.wav', '.aac', '.m4a', '.wma', '.ogg',
        '.ape', '.opus', '.alac', '.aiff'
    }

    def __init__(self, db: DatabaseInterface):
        self.db = db

    def create_task(self, task_data: Dict) -> StrmTask:
        """创建任务"""
        now = time.time()

        # 生成任务 ID
        task_id = f"task_{int(now * 1000)}"

        # 创建任务对象
        task = StrmTask(
            task_id=task_id,
            task_name=task_data['task_name'],
            drive_id=task_data['drive_id'],
            source_cid=task_data['source_cid'],
            output_dir=task_data['output_dir'],
            base_url=task_data.get('base_url'),
            include_video=task_data.get('include_video', True),
            include_audio=task_data.get('include_audio', False),
            custom_extensions=task_data.get('custom_extensions'),
            schedule_enabled=task_data.get('schedule_enabled', False),
            schedule_type=task_data.get('schedule_type'),
            schedule_config=task_data.get('schedule_config'),
            watch_enabled=task_data.get('watch_enabled', False),
            watch_interval=task_data.get('watch_interval', 3600),
            delete_orphans=task_data.get('delete_orphans', True),
            preserve_structure=task_data.get('preserve_structure', True),
            created_at=now,
            updated_at=now
        )

        # 保存到数据库
        data = task.to_dict()
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' if hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory') else '%s'] * len(data))
        query = f"INSERT INTO strm_tasks ({columns}) VALUES ({placeholders})"

        self.db.execute(query, tuple(data.values()))
        logger.info(f"Created task: {task_id}")

        return task

    def get_task(self, task_id: str) -> Optional[StrmTask]:
        """获取任务"""
        query = "SELECT * FROM strm_tasks WHERE task_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        row = self.db.fetchone(query, (task_id,))
        if row:
            return StrmTask.from_dict(row)
        return None

    def list_tasks(self, drive_id: Optional[str] = None) -> List[StrmTask]:
        """列出任务"""
        if drive_id:
            query = "SELECT * FROM strm_tasks WHERE drive_id = ? ORDER BY created_at DESC"
            if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
                query = query.replace('?', '%s')
            rows = self.db.fetchall(query, (drive_id,))
        else:
            query = "SELECT * FROM strm_tasks ORDER BY created_at DESC"
            rows = self.db.fetchall(query)

        return [StrmTask.from_dict(row) for row in rows]

    def update_task(self, task_id: str, updates: Dict) -> bool:
        """更新任务"""
        # 获取现有任务
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        # 更新字段
        updates['updated_at'] = time.time()

        # 处理特殊字段
        if 'custom_extensions' in updates and updates['custom_extensions']:
            updates['custom_extensions'] = json.dumps(updates['custom_extensions'])

        if 'schedule_config' in updates and updates['schedule_config']:
            updates['schedule_config'] = json.dumps(updates['schedule_config'])

        # 转换布尔值
        for field in ['include_video', 'include_audio', 'schedule_enabled',
                      'watch_enabled', 'delete_orphans', 'preserve_structure']:
            if field in updates:
                updates[field] = 1 if updates[field] else 0

        # 构建更新语句
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            set_clause = set_clause.replace('?', '%s')

        query = f"UPDATE strm_tasks SET {set_clause} WHERE task_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('task_id = ?', 'task_id = %s')

        params = tuple(list(updates.values()) + [task_id])
        self.db.execute(query, params)

        logger.info(f"Updated task: {task_id}")
        return True

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        query = "DELETE FROM strm_tasks WHERE task_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        self.db.execute(query, (task_id,))
        logger.info(f"Deleted task: {task_id}")
        return True

    def update_task_status(self, task_id: str, status: str, message: str = None):
        """更新任务状态"""
        updates = {
            'status': status,
            'updated_at': time.time()
        }

        if message:
            updates['last_run_message'] = message

        if status in ['success', 'error']:
            updates['last_run_status'] = status
            updates['last_run_time'] = time.time()

        self.update_task(task_id, updates)

    def get_task_statistics(self, task_id: str) -> Dict:
        """获取任务统计"""
        task = self.get_task(task_id)
        if not task:
            return {}

        # 获取 STRM 记录数
        query = "SELECT COUNT(*) as count FROM strm_records WHERE task_id = ? AND status = 'active'"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        result = self.db.fetchone(query, (task_id,))
        active_records = result['count'] if result else 0

        # 获取最近日志
        logs = self.get_task_logs(task_id, limit=1)
        last_log = logs[0] if logs else None

        return {
            'task_id': task_id,
            'task_name': task.task_name,
            'status': task.status,
            'total_runs': task.total_runs,
            'total_files_generated': task.total_files_generated,
            'active_records': active_records,
            'last_run_time': task.last_run_time,
            'last_run_status': task.last_run_status,
            'last_run_message': task.last_run_message,
            'last_log': last_log
        }

    # STRM 记录管理

    def get_strm_records(self, task_id: str, status: str = 'active') -> List[Dict]:
        """获取 STRM 记录"""
        query = "SELECT * FROM strm_records WHERE task_id = ?"
        params = [task_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        return self.db.fetchall(query, tuple(params))

    def add_strm_record(self, task_id: str, record: Dict) -> bool:
        """添加 STRM 记录"""
        now = time.time()
        record_id = f"{task_id}_{record['pick_code']}"

        data = {
            'record_id': record_id,
            'task_id': task_id,
            'file_id': record['file_id'],
            'pick_code': record['pick_code'],
            'file_name': record['file_name'],
            'file_size': record.get('file_size'),
            'file_path': record.get('file_path'),
            'strm_path': record['strm_path'],
            'strm_content': record['strm_content'],
            'status': 'active',
            'created_at': now,
            'updated_at': now
        }

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' if hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory') else '%s'] * len(data))
        query = f"INSERT INTO strm_records ({columns}) VALUES ({placeholders})"

        try:
            self.db.execute(query, tuple(data.values()))
            return True
        except Exception as e:
            logger.error(f"Failed to add STRM record: {e}")
            return False

    def update_strm_record(self, record_id: str, updates: Dict) -> bool:
        """更新 STRM 记录"""
        updates['updated_at'] = time.time()

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            set_clause = set_clause.replace('?', '%s')

        query = f"UPDATE strm_records SET {set_clause} WHERE record_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('record_id = ?', 'record_id = %s')

        params = tuple(list(updates.values()) + [record_id])

        try:
            self.db.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to update STRM record: {e}")
            return False

    def delete_strm_record(self, record_id: str) -> bool:
        """删除 STRM 记录"""
        query = "DELETE FROM strm_records WHERE record_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        try:
            self.db.execute(query, (record_id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete STRM record: {e}")
            return False

    def get_record_by_pick_code(self, task_id: str, pick_code: str) -> Optional[Dict]:
        """根据 pick_code 获取记录"""
        query = "SELECT * FROM strm_records WHERE task_id = ? AND pick_code = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        return self.db.fetchone(query, (task_id, pick_code))

    def get_record_by_file_id(self, task_id: str, file_id: str) -> Optional[Dict]:
        """根据 file_id 获取记录"""
        query = "SELECT * FROM strm_records WHERE task_id = ? AND file_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        return self.db.fetchone(query, (task_id, file_id))

    def cleanup_orphan_records(self, task_id: str, current_file_ids: List[str]) -> int:
        """清理孤立记录"""
        # 获取所有活跃记录
        records = self.get_strm_records(task_id, status='active')

        deleted_count = 0
        for record in records:
            if record['file_id'] not in current_file_ids:
                # 删除物理 STRM 文件
                if os.path.exists(record['strm_path']):
                    try:
                        os.remove(record['strm_path'])
                        logger.info(f"Deleted orphan STRM file: {record['strm_path']}")
                    except Exception as e:
                        logger.error(f"Failed to delete STRM file: {e}")

                # 删除数据库记录
                self.delete_strm_record(record['record_id'])
                deleted_count += 1

        return deleted_count

    # 文件快照管理

    def create_snapshot(self, task_id: str, files: List[Dict]) -> bool:
        """创建文件快照"""
        now = time.time()

        # 删除旧快照
        query = "DELETE FROM file_snapshots WHERE task_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')
        self.db.execute(query, (task_id,))

        # 插入新快照
        for file_info in files:
            snapshot_id = f"{task_id}_{file_info['file_id']}"
            snapshot_hash = self._compute_file_hash(file_info)

            data = {
                'snapshot_id': snapshot_id,
                'task_id': task_id,
                'file_id': file_info['file_id'],
                'pick_code': file_info['pick_code'],
                'file_name': file_info['file_name'],
                'file_size': file_info.get('file_size'),
                'file_path': file_info.get('file_path'),
                'modified_time': file_info.get('modified_time'),
                'snapshot_time': now,
                'snapshot_hash': snapshot_hash
            }

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' if hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory') else '%s'] * len(data))
            query = f"INSERT INTO file_snapshots ({columns}) VALUES ({placeholders})"

            try:
                self.db.execute(query, tuple(data.values()))
            except Exception as e:
                logger.error(f"Failed to create snapshot for file {file_info['file_id']}: {e}")

        return True

    def get_snapshot(self, task_id: str) -> List[Dict]:
        """获取文件快照"""
        query = "SELECT * FROM file_snapshots WHERE task_id = ?"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        return self.db.fetchall(query, (task_id,))

    def detect_changes(self, task_id: str, current_files: List[Dict]) -> Dict:
        """检测文件变化"""
        # 获取上次快照
        snapshot = {s['file_id']: s for s in self.get_snapshot(task_id)}

        # 构建当前文件映射
        current = {f['file_id']: f for f in current_files}

        # 检测变化
        added = [f for fid, f in current.items() if fid not in snapshot]
        deleted = [s for fid, s in snapshot.items() if fid not in current]
        modified = []

        for fid in set(snapshot.keys()) & set(current.keys()):
            if self._file_changed(snapshot[fid], current[fid]):
                modified.append(current[fid])

        return {
            'added': added,
            'deleted': deleted,
            'modified': modified
        }

    def _compute_file_hash(self, file_info: Dict) -> str:
        """计算文件哈希"""
        hash_data = f"{file_info['file_id']}_{file_info['file_name']}_{file_info.get('file_size', 0)}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    def _file_changed(self, old: Dict, new: Dict) -> bool:
        """检查文件是否变化"""
        return (old['file_name'] != new['file_name'] or
                old.get('file_size') != new.get('file_size') or
                old.get('modified_time') != new.get('modified_time'))

    # 任务日志管理

    def add_task_log(self, task_id: str, log_data: Dict) -> bool:
        """添加任务日志"""
        log_id = f"{task_id}_{int(log_data['start_time'] * 1000)}"

        data = {
            'log_id': log_id,
            'task_id': task_id,
            'start_time': log_data['start_time'],
            'end_time': log_data.get('end_time'),
            'duration': log_data.get('duration'),
            'status': log_data['status'],
            'message': log_data.get('message'),
            'error_trace': log_data.get('error_trace'),
            'files_scanned': log_data.get('files_scanned', 0),
            'files_added': log_data.get('files_added', 0),
            'files_updated': log_data.get('files_updated', 0),
            'files_deleted': log_data.get('files_deleted', 0),
            'files_skipped': log_data.get('files_skipped', 0)
        }

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' if hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory') else '%s'] * len(data))
        query = f"INSERT INTO task_logs ({columns}) VALUES ({placeholders})"

        try:
            self.db.execute(query, tuple(data.values()))
            return True
        except Exception as e:
            logger.error(f"Failed to add task log: {e}")
            return False

    def get_task_logs(self, task_id: str, limit: int = 50) -> List[Dict]:
        """获取任务日志"""
        query = f"SELECT * FROM task_logs WHERE task_id = ? ORDER BY start_time DESC LIMIT {limit}"
        if not (hasattr(self.db, 'conn') and hasattr(self.db.conn, 'row_factory')):
            query = query.replace('?', '%s')

        return self.db.fetchall(query, (task_id,))

    # 文件过滤

    def should_include_file(self, task: StrmTask, file_name: str) -> bool:
        """判断是否应该包含文件"""
        ext = os.path.splitext(file_name)[1].lower()

        # 自定义扩展名优先
        if task.custom_extensions:
            return ext in [e.lower() if e.startswith('.') else f'.{e.lower()}'
                          for e in task.custom_extensions]

        # 默认过滤规则
        if task.include_video and ext in self.VIDEO_EXTENSIONS:
            return True

        if task.include_audio and ext in self.AUDIO_EXTENSIONS:
            return True

        return False
