"""
数据库迁移工具
"""
import logging
from typing import List
from .base import DatabaseInterface

logger = logging.getLogger(__name__)


class Migration:
    """数据库迁移基类"""

    def __init__(self, version: int, description: str):
        self.version = version
        self.description = description

    def up_sqlite(self, db: DatabaseInterface):
        """SQLite 升级脚本"""
        raise NotImplementedError

    def up_mysql(self, db: DatabaseInterface):
        """MySQL 升级脚本"""
        raise NotImplementedError


class Migration001_AddLastEventId(Migration):
    """添加 last_event_id 字段到 strm_tasks 表"""

    def __init__(self):
        super().__init__(1, "Add last_event_id to strm_tasks")

    def up_sqlite(self, db: DatabaseInterface):
        """SQLite 升级脚本"""
        try:
            # 检查列是否已存在
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM pragma_table_info('strm_tasks') WHERE name='last_event_id'"
            )

            if result and result['count'] == 0:
                # 添加列
                db.execute("ALTER TABLE strm_tasks ADD COLUMN last_event_id INTEGER DEFAULT 0")
                logger.info("Added last_event_id column to strm_tasks table (SQLite)")
            else:
                logger.info("Column last_event_id already exists in strm_tasks table (SQLite)")
        except Exception as e:
            logger.error(f"Failed to add last_event_id column (SQLite): {e}")
            raise

    def up_mysql(self, db: DatabaseInterface):
        """MySQL 升级脚本"""
        try:
            # 检查列是否已存在
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'strm_tasks' AND COLUMN_NAME = 'last_event_id'"
            )

            if result and result['count'] == 0:
                # 添加列
                db.execute("ALTER TABLE strm_tasks ADD COLUMN last_event_id BIGINT DEFAULT 0")
                logger.info("Added last_event_id column to strm_tasks table (MySQL)")
            else:
                logger.info("Column last_event_id already exists in strm_tasks table (MySQL)")
        except Exception as e:
            logger.error(f"Failed to add last_event_id column (MySQL): {e}")
            raise


class Migration002_AddProgressFields(Migration):
    """添加进度字段到 strm_tasks 表"""

    def __init__(self):
        super().__init__(2, "Add progress fields to strm_tasks")

    def up_sqlite(self, db: DatabaseInterface):
        """SQLite 升级脚本"""
        try:
            # 检查 total_files 列是否已存在
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM pragma_table_info('strm_tasks') WHERE name='total_files'"
            )

            if result and result['count'] == 0:
                db.execute("ALTER TABLE strm_tasks ADD COLUMN total_files INTEGER DEFAULT 0")
                logger.info("Added total_files column to strm_tasks table (SQLite)")

            # 检查 current_file_index 列是否已存在
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM pragma_table_info('strm_tasks') WHERE name='current_file_index'"
            )

            if result and result['count'] == 0:
                db.execute("ALTER TABLE strm_tasks ADD COLUMN current_file_index INTEGER DEFAULT 0")
                logger.info("Added current_file_index column to strm_tasks table (SQLite)")
        except Exception as e:
            logger.error(f"Failed to add progress fields (SQLite): {e}")
            raise

    def up_mysql(self, db: DatabaseInterface):
        """MySQL 升级脚本"""
        try:
            # 检查 total_files 列是否已存在
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'strm_tasks' AND COLUMN_NAME = 'total_files'"
            )

            if result and result['count'] == 0:
                db.execute("ALTER TABLE strm_tasks ADD COLUMN total_files INT DEFAULT 0")
                logger.info("Added total_files column to strm_tasks table (MySQL)")

            # 检查 current_file_index 列是否已存在
            result = db.fetchone(
                "SELECT COUNT(*) as count FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'strm_tasks' AND COLUMN_NAME = 'current_file_index'"
            )

            if result and result['count'] == 0:
                db.execute("ALTER TABLE strm_tasks ADD COLUMN current_file_index INT DEFAULT 0")
                logger.info("Added current_file_index column to strm_tasks table (MySQL)")
        except Exception as e:
            logger.error(f"Failed to add progress fields (MySQL): {e}")
            raise


# 所有迁移列表（按版本顺序）
MIGRATIONS: List[Migration] = [
    Migration001_AddLastEventId(),
    Migration002_AddProgressFields(),
]


class MigrationManager:
    """迁移管理器"""

    def __init__(self, db: DatabaseInterface, db_type: str):
        """
        Args:
            db: 数据库接口
            db_type: 数据库类型 ('sqlite' 或 'mysql')
        """
        self.db = db
        self.db_type = db_type
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """确保迁移记录表存在"""
        if self.db_type == 'sqlite':
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at REAL NOT NULL
                )
            """)
        else:  # mysql
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INT PRIMARY KEY,
                    description VARCHAR(255) NOT NULL,
                    applied_at DOUBLE NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

    def get_current_version(self) -> int:
        """获取当前数据库版本"""
        result = self.db.fetchone("SELECT MAX(version) as version FROM schema_migrations")
        return result['version'] if result and result['version'] else 0

    def run_migrations(self):
        """运行所有待执行的迁移"""
        current_version = self.get_current_version()
        logger.info(f"Current database version: {current_version}")

        pending_migrations = [m for m in MIGRATIONS if m.version > current_version]

        if not pending_migrations:
            logger.info("No pending migrations")
            return

        logger.info(f"Found {len(pending_migrations)} pending migrations")

        for migration in pending_migrations:
            logger.info(f"Running migration {migration.version}: {migration.description}")

            try:
                # 执行迁移
                if self.db_type == 'sqlite':
                    migration.up_sqlite(self.db)
                else:
                    migration.up_mysql(self.db)

                # 记录迁移
                import time
                self.db.execute(
                    "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
                    (migration.version, migration.description, time.time())
                )

                logger.info(f"Migration {migration.version} completed successfully")

            except Exception as e:
                logger.error(f"Migration {migration.version} failed: {e}")
                raise

        logger.info("All migrations completed successfully")
