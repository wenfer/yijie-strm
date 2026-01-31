"""
MySQL 数据库实现
"""
import logging
from typing import Dict, List, Optional, Any
from .base import DatabaseInterface

logger = logging.getLogger(__name__)


class MySQLDatabase(DatabaseInterface):
    """MySQL 数据库实现"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None

        # 延迟导入 MySQL 驱动
        try:
            import pymysql
            self.pymysql = pymysql
        except ImportError:
            raise ImportError(
                "pymysql is required for MySQL support. "
                "Install it with: pip install pymysql"
            )

    def connect(self):
        """连接数据库"""
        try:
            self.conn = self.pymysql.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                cursorclass=self.pymysql.cursors.DictCursor
            )
            logger.info(f"mysql_db.py:46 - Connected to MySQL database: {self.database}")
            self.init_schema()
        except Exception as e:
            logger.error(f"mysql_db.py:49 - Failed to connect to MySQL database: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("mysql_db.py:57 - MySQL database connection closed")

    def execute(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 语句"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            with self.conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor
        except Exception as e:
            self.conn.rollback()
            logger.error(f"mysql_db.py:75 - Failed to execute query: {e}")
            raise

    def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            with self.conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"mysql_db.py:92 - Failed to fetch one: {e}")
            raise

    def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """查询多条记录"""
        if not self.conn:
            raise RuntimeError("Database not connected")

        try:
            with self.conn.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"mysql_db.py:109 - Failed to fetch all: {e}")
            raise

    def init_schema(self):
        """初始化数据库表结构"""
        schema = """
        CREATE TABLE IF NOT EXISTS drives (
            drive_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            drive_type VARCHAR(50) NOT NULL DEFAULT '115',
            token_file VARCHAR(500) NOT NULL,
            created_at DOUBLE NOT NULL,
            last_used DOUBLE NOT NULL,
            INDEX idx_drives_last_used (last_used DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS settings (
            `key` VARCHAR(255) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DOUBLE NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS strm_tasks (
            task_id VARCHAR(255) PRIMARY KEY,
            task_name VARCHAR(255) NOT NULL,
            drive_id VARCHAR(255) NOT NULL,
            source_cid VARCHAR(255) NOT NULL,
            output_dir VARCHAR(500) NOT NULL,
            base_url VARCHAR(500),

            include_video TINYINT DEFAULT 1,
            include_audio TINYINT DEFAULT 0,
            custom_extensions TEXT,

            schedule_enabled TINYINT DEFAULT 0,
            schedule_type VARCHAR(50),
            schedule_config TEXT,

            watch_enabled TINYINT DEFAULT 0,
            watch_interval INT DEFAULT 3600,

            delete_orphans TINYINT DEFAULT 1,
            preserve_structure TINYINT DEFAULT 1,
            overwrite_strm TINYINT DEFAULT 0,

            status VARCHAR(50) DEFAULT 'idle',
            last_run_time DOUBLE,
            last_run_status VARCHAR(50),
            last_run_message TEXT,
            next_run_time DOUBLE,

            total_runs INT DEFAULT 0,
            total_files_generated INT DEFAULT 0,

            last_event_id BIGINT DEFAULT 0,

            created_at DOUBLE NOT NULL,
            updated_at DOUBLE NOT NULL,

            INDEX idx_strm_tasks_drive_id (drive_id),
            INDEX idx_strm_tasks_status (status),
            INDEX idx_strm_tasks_next_run (next_run_time),
            FOREIGN KEY (drive_id) REFERENCES drives(drive_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS strm_records (
            record_id VARCHAR(255) PRIMARY KEY,
            task_id VARCHAR(255) NOT NULL,

            file_id VARCHAR(255) NOT NULL,
            pick_code VARCHAR(255) NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            file_size BIGINT,
            file_path TEXT,

            strm_path VARCHAR(1000) NOT NULL,
            strm_content TEXT NOT NULL,

            status VARCHAR(50) DEFAULT 'active',
            created_at DOUBLE NOT NULL,
            updated_at DOUBLE NOT NULL,

            INDEX idx_strm_records_task_id (task_id),
            INDEX idx_strm_records_pick_code (pick_code),
            INDEX idx_strm_records_file_id (file_id),
            UNIQUE INDEX idx_strm_records_unique (task_id, pick_code),
            FOREIGN KEY (task_id) REFERENCES strm_tasks(task_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS file_snapshots (
            snapshot_id VARCHAR(255) PRIMARY KEY,
            task_id VARCHAR(255) NOT NULL,

            file_id VARCHAR(255) NOT NULL,
            pick_code VARCHAR(255) NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            file_size BIGINT,
            file_path TEXT,
            modified_time DOUBLE,

            snapshot_time DOUBLE NOT NULL,
            snapshot_hash VARCHAR(255),

            INDEX idx_file_snapshots_task_id (task_id),
            INDEX idx_file_snapshots_file_id (file_id),
            UNIQUE INDEX idx_file_snapshots_unique (task_id, file_id),
            FOREIGN KEY (task_id) REFERENCES strm_tasks(task_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS task_logs (
            log_id VARCHAR(255) PRIMARY KEY,
            task_id VARCHAR(255) NOT NULL,

            start_time DOUBLE NOT NULL,
            end_time DOUBLE,
            duration DOUBLE,

            status VARCHAR(50) NOT NULL,
            message TEXT,
            error_trace TEXT,

            files_scanned INT DEFAULT 0,
            files_added INT DEFAULT 0,
            files_updated INT DEFAULT 0,
            files_deleted INT DEFAULT 0,
            files_skipped INT DEFAULT 0,

            INDEX idx_task_logs_task_id (task_id),
            INDEX idx_task_logs_start_time (start_time DESC),
            FOREIGN KEY (task_id) REFERENCES strm_tasks(task_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        try:
            for statement in schema.strip().split(';'):
                statement = statement.strip()
                if statement:
                    self.execute(statement)
            logger.info("mysql_db.py:272 - Database schema initialized")
        except Exception as e:
            logger.error(f"mysql_db.py:274 - Failed to initialize schema: {e}")
            raise
