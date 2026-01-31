"""
SQLite 数据库实现
"""
import sqlite3
import logging
import os
from typing import Dict, List, Optional, Any
from .base import DatabaseInterface

logger = logging.getLogger(__name__)


class SQLiteDatabase(DatabaseInterface):
    """SQLite 数据库实现"""

    def __init__(self, db_path: str):
        self.db_path = os.path.expanduser(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """连接数据库"""
        try:
            # 确保目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # 允许跨线程使用连接（用于调度器线程）
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"sqlite_db.py:30 - Connected to SQLite database: {self.db_path}")
            self.init_schema()
        except Exception as e:
            logger.error(f"sqlite_db.py:33 - Failed to connect to SQLite database: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("sqlite_db.py:41 - SQLite database connection closed")

    def execute(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 语句"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor
        except Exception as e:
            self.conn.rollback()
            logger.error(f"sqlite_db.py:59 - Failed to execute query: {e}")
            raise

    def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"sqlite_db.py:77 - Failed to fetch one: {e}")
            raise

    def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """查询多条记录"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"sqlite_db.py:95 - Failed to fetch all: {e}")
            raise

    def init_schema(self):
        """初始化数据库表结构"""
        schema = """
        CREATE TABLE IF NOT EXISTS drives (
            drive_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            drive_type TEXT NOT NULL DEFAULT '115',
            token_file TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_used REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS strm_tasks (
            task_id TEXT PRIMARY KEY,
            task_name TEXT NOT NULL,
            drive_id TEXT NOT NULL,
            source_cid TEXT NOT NULL,
            output_dir TEXT NOT NULL,
            base_url TEXT,

            include_video INTEGER DEFAULT 1,
            include_audio INTEGER DEFAULT 0,
            custom_extensions TEXT,

            schedule_enabled INTEGER DEFAULT 0,
            schedule_type TEXT,
            schedule_config TEXT,

            watch_enabled INTEGER DEFAULT 0,
            watch_interval INTEGER DEFAULT 3600,

            delete_orphans INTEGER DEFAULT 1,
            preserve_structure INTEGER DEFAULT 1,
            overwrite_strm INTEGER DEFAULT 0,

            status TEXT DEFAULT 'idle',
            last_run_time REAL,
            last_run_status TEXT,
            last_run_message TEXT,
            next_run_time REAL,

            total_runs INTEGER DEFAULT 0,
            total_files_generated INTEGER DEFAULT 0,

            last_event_id INTEGER DEFAULT 0,

            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,

            FOREIGN KEY (drive_id) REFERENCES drives(drive_id)
        );

        CREATE TABLE IF NOT EXISTS strm_records (
            record_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,

            file_id TEXT NOT NULL,
            pick_code TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER,
            file_path TEXT,

            strm_path TEXT NOT NULL,
            strm_content TEXT NOT NULL,

            status TEXT DEFAULT 'active',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,

            FOREIGN KEY (task_id) REFERENCES strm_tasks(task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS file_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,

            file_id TEXT NOT NULL,
            pick_code TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER,
            file_path TEXT,
            modified_time REAL,

            snapshot_time REAL NOT NULL,
            snapshot_hash TEXT,

            FOREIGN KEY (task_id) REFERENCES strm_tasks(task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS task_logs (
            log_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,

            start_time REAL NOT NULL,
            end_time REAL,
            duration REAL,

            status TEXT NOT NULL,
            message TEXT,
            error_trace TEXT,

            files_scanned INTEGER DEFAULT 0,
            files_added INTEGER DEFAULT 0,
            files_updated INTEGER DEFAULT 0,
            files_deleted INTEGER DEFAULT 0,
            files_skipped INTEGER DEFAULT 0,

            FOREIGN KEY (task_id) REFERENCES strm_tasks(task_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_drives_last_used ON drives(last_used DESC);
        CREATE INDEX IF NOT EXISTS idx_strm_tasks_drive_id ON strm_tasks(drive_id);
        CREATE INDEX IF NOT EXISTS idx_strm_tasks_status ON strm_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_strm_tasks_next_run ON strm_tasks(next_run_time);
        CREATE INDEX IF NOT EXISTS idx_strm_records_task_id ON strm_records(task_id);
        CREATE INDEX IF NOT EXISTS idx_strm_records_pick_code ON strm_records(pick_code);
        CREATE INDEX IF NOT EXISTS idx_strm_records_file_id ON strm_records(file_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_strm_records_unique ON strm_records(task_id, pick_code);
        CREATE INDEX IF NOT EXISTS idx_file_snapshots_task_id ON file_snapshots(task_id);
        CREATE INDEX IF NOT EXISTS idx_file_snapshots_file_id ON file_snapshots(file_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_file_snapshots_unique ON file_snapshots(task_id, file_id);
        CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id);
        CREATE INDEX IF NOT EXISTS idx_task_logs_start_time ON task_logs(start_time DESC);
        """

        try:
            self.conn.executescript(schema)
            self.conn.commit()
            logger.info("sqlite_db.py:247 - Database schema initialized")
        except Exception as e:
            logger.error(f"sqlite_db.py:249 - Failed to initialize schema: {e}")
            raise
