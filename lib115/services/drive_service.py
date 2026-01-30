"""
网盘管理服务
支持多个 115 网盘账号的管理
使用数据库存储（支持 SQLite 和 MySQL）
"""
from __future__ import annotations
import json
import logging
import os
import time
from typing import Dict, List, Optional
from pathlib import Path

from ..config import AppConfig, default_config
from ..auth.token_manager import TokenManager
from ..db import get_database, DatabaseInterface

logger = logging.getLogger(__name__)


class Drive:
    """网盘账号"""

    def __init__(
        self,
        drive_id: str,
        name: str,
        drive_type: str = "115",
        token_file: Optional[str] = None,
        created_at: Optional[float] = None,
        last_used: Optional[float] = None,
    ):
        self.drive_id = drive_id
        self.name = name
        self.drive_type = drive_type
        self.token_file = token_file or f"~/.115_token_{drive_id}.json"
        self.created_at = created_at or time.time()
        self.last_used = last_used or time.time()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "drive_id": self.drive_id,
            "name": self.name,
            "drive_type": self.drive_type,
            "token_file": self.token_file,
            "created_at": self.created_at,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Drive':
        """从字典创建"""
        return cls(
            drive_id=data["drive_id"],
            name=data["name"],
            drive_type=data.get("drive_type", "115"),
            token_file=data.get("token_file"),
            created_at=data.get("created_at"),
            last_used=data.get("last_used"),
        )

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        token_path = os.path.expanduser(self.token_file)
        if not os.path.exists(token_path):
            return False

        try:
            with open(token_path, 'r', encoding='utf-8') as f:
                token_data = json.load(f)

            if not isinstance(token_data, dict) or "data" not in token_data:
                return False

            # 检查 token 是否过期
            timestamp = token_data.get("timestamp", 0)
            expires_in = token_data.get("data", {}).get("expires_in", 7200)
            expire_time = timestamp + expires_in

            return time.time() < expire_time
        except Exception as e:
            logger.error(f"Failed to check authentication for drive {self.drive_id}: {e}")
            return False


class DriveService:
    """网盘管理服务（使用数据库存储）"""

    def __init__(self, config: AppConfig = None):
        self.config = config or default_config
        self.db: Optional[DatabaseInterface] = None
        self._current_drive_id: Optional[str] = None
        self._initialize_database()
        self._migrate_from_json()

    def _initialize_database(self):
        """初始化数据库连接"""
        try:
            self.db = get_database(self.config)
            self.db.connect()
            logger.info("Database initialized successfully")

            # 加载当前网盘 ID
            self._load_current_drive()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _load_current_drive(self):
        """从数据库加载当前网盘 ID"""
        try:
            result = self.db.fetchone(
                "SELECT value FROM settings WHERE key = ?",
                ("current_drive_id",)
            )
            if result:
                self._current_drive_id = result["value"]
                logger.info(f"Loaded current drive: {self._current_drive_id}")
        except Exception as e:
            logger.error(f"Failed to load current drive: {e}")

    def _save_current_drive(self):
        """保存当前网盘 ID 到数据库"""
        try:
            if self._current_drive_id:
                self.db.execute(
                    """
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    ("current_drive_id", self._current_drive_id, time.time())
                )
            else:
                self.db.execute(
                    "DELETE FROM settings WHERE key = ?",
                    ("current_drive_id",)
                )
        except Exception as e:
            logger.error(f"Failed to save current drive: {e}")

    def _migrate_from_json(self):
        """从 JSON 文件迁移数据到数据库"""
        drives_file = os.path.expanduser("~/.115_drives.json")
        if not os.path.exists(drives_file):
            return

        try:
            # 检查数据库是否已有数据
            result = self.db.fetchone("SELECT COUNT(*) as count FROM drives")
            if result and result["count"] > 0:
                logger.info("Database already has data, skipping migration")
                return

            # 读取 JSON 文件
            with open(drives_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            drives = data.get("drives", {})
            current_drive_id = data.get("current_drive_id")

            # 迁移网盘数据
            for drive_id, drive_data in drives.items():
                drive = Drive.from_dict(drive_data)
                self.db.execute(
                    """
                    INSERT INTO drives (drive_id, name, drive_type, token_file, created_at, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (drive.drive_id, drive.name, drive.drive_type, drive.token_file,
                     drive.created_at, drive.last_used)
                )

            # 迁移当前网盘 ID
            if current_drive_id:
                self._current_drive_id = current_drive_id
                self._save_current_drive()

            logger.info(f"Migrated {len(drives)} drives from JSON to database")

            # 备份 JSON 文件
            backup_file = drives_file + ".backup"
            os.rename(drives_file, backup_file)
            logger.info(f"Backed up JSON file to {backup_file}")

        except Exception as e:
            logger.error(f"Failed to migrate from JSON: {e}")

    def list_drives(self) -> List[Dict]:
        """获取网盘列表"""
        try:
            rows = self.db.fetchall(
                "SELECT * FROM drives ORDER BY last_used DESC"
            )

            drives = []
            for row in rows:
                drive = Drive.from_dict(row)
                drive_info = drive.to_dict()
                drive_info["is_authenticated"] = drive.is_authenticated()
                drive_info["is_current"] = drive.drive_id == self._current_drive_id
                drives.append(drive_info)

            return drives
        except Exception as e:
            logger.error(f"Failed to list drives: {e}")
            return []

    def get_drive(self, drive_id: str) -> Optional[Drive]:
        """获取指定网盘"""
        try:
            row = self.db.fetchone(
                "SELECT * FROM drives WHERE drive_id = ?",
                (drive_id,)
            )
            return Drive.from_dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get drive {drive_id}: {e}")
            return None

    def get_current_drive(self) -> Optional[Drive]:
        """获取当前网盘"""
        if not self._current_drive_id:
            return None
        return self.get_drive(self._current_drive_id)

    def add_drive(self, name: str, drive_type: str = "115") -> Drive:
        """添加网盘"""
        # 生成唯一 ID
        drive_id = f"{drive_type}_{int(time.time() * 1000)}"

        drive = Drive(
            drive_id=drive_id,
            name=name,
            drive_type=drive_type,
        )

        try:
            self.db.execute(
                """
                INSERT INTO drives (drive_id, name, drive_type, token_file, created_at, last_used)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (drive.drive_id, drive.name, drive.drive_type, drive.token_file,
                 drive.created_at, drive.last_used)
            )

            # 如果是第一个网盘，设置为当前网盘
            if not self._current_drive_id:
                self._current_drive_id = drive_id
                self._save_current_drive()

            logger.info(f"Added drive: {drive_id} ({name})")
            return drive
        except Exception as e:
            logger.error(f"Failed to add drive: {e}")
            raise

    def remove_drive(self, drive_id: str) -> bool:
        """删除网盘"""
        try:
            drive = self.get_drive(drive_id)
            if not drive:
                return False

            # 删除 token 文件
            token_path = os.path.expanduser(drive.token_file)
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    logger.info(f"Removed token file: {token_path}")
                except Exception as e:
                    logger.error(f"Failed to remove token file: {e}")

            # 从数据库删除
            self.db.execute(
                "DELETE FROM drives WHERE drive_id = ?",
                (drive_id,)
            )

            # 如果删除的是当前网盘，切换到其他网盘
            if self._current_drive_id == drive_id:
                drives = self.list_drives()
                if drives:
                    self._current_drive_id = drives[0]["drive_id"]
                else:
                    self._current_drive_id = None
                self._save_current_drive()

            logger.info(f"Removed drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove drive {drive_id}: {e}")
            return False

    def set_current_drive(self, drive_id: str) -> bool:
        """设置当前网盘"""
        try:
            drive = self.get_drive(drive_id)
            if not drive:
                return False

            self._current_drive_id = drive_id

            # 更新最后使用时间
            self.db.execute(
                "UPDATE drives SET last_used = ? WHERE drive_id = ?",
                (time.time(), drive_id)
            )

            self._save_current_drive()
            logger.info(f"Set current drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set current drive {drive_id}: {e}")
            return False

    def update_drive(self, drive_id: str, name: Optional[str] = None) -> bool:
        """更新网盘信息"""
        try:
            drive = self.get_drive(drive_id)
            if not drive:
                return False

            if name:
                self.db.execute(
                    "UPDATE drives SET name = ? WHERE drive_id = ?",
                    (name, drive_id)
                )

            logger.info(f"Updated drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update drive {drive_id}: {e}")
            return False

    def mark_drive_unauthenticated(self, drive_id: str) -> bool:
        """标记网盘为未认证状态（删除 token 文件）"""
        try:
            drive = self.get_drive(drive_id)
            if not drive:
                logger.warning(f"Drive not found: {drive_id}")
                return False

            # 删除 token 文件
            token_path = os.path.expanduser(drive.token_file)
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    logger.warning(f"Removed invalid token file for drive {drive_id}: {token_path}")
                except Exception as e:
                    logger.error(f"Failed to remove token file: {e}")
                    return False

            logger.warning(f"Drive {drive_id} marked as unauthenticated")
            return True
        except Exception as e:
            logger.error(f"Failed to mark drive {drive_id} as unauthenticated: {e}")
            return False

    def get_token_manager(self, drive_id: Optional[str] = None) -> Optional[TokenManager]:
        """获取指定网盘的 TokenManager"""
        if not drive_id:
            drive_id = self._current_drive_id

        if not drive_id:
            return None

        drive = self.get_drive(drive_id)
        if not drive:
            return None

        # 创建临时配置，使用该网盘的 token 文件
        config = AppConfig.from_env()
        config.auth.TOKEN_FILE_PATH = os.path.expanduser(drive.token_file)

        return TokenManager(config)

    def get_client(self, drive_id: Optional[str] = None):
        """获取指定网盘的 Client115 实例"""
        if not drive_id:
            drive_id = self._current_drive_id

        if not drive_id:
            logger.error("No drive_id specified and no current drive set")
            return None

        drive = self.get_drive(drive_id)
        if not drive:
            logger.error(f"Drive not found: {drive_id}")
            return None

        # 检查是否已认证
        if not drive.is_authenticated():
            logger.error(f"Drive {drive_id} is not authenticated")
            return None

        # 创建临时配置，使用该网盘的 token 文件
        from ..config import AppConfig
        from ..api.client import Client115

        config = AppConfig.from_env()
        config.auth.TOKEN_FILE_PATH = os.path.expanduser(drive.token_file)

        try:
            client = Client115(config, auto_start_watcher=False)

            # 验证 token 是否有效（尝试获取 token，超时时间设为 5 秒）
            token = client.token_watcher.get_token(timeout=5)
            if not token:
                logger.error(f"Failed to get valid token for drive {drive_id}")
                # 标记为未认证
                self.mark_drive_unauthenticated(drive_id)
                return None

            return client
        except Exception as e:
            logger.error(f"Failed to create client for drive {drive_id}: {e}")
            # 如果是认证相关错误，标记为未认证
            if 'token' in str(e).lower() or 'auth' in str(e).lower():
                self.mark_drive_unauthenticated(drive_id)
            return None

    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
            self.db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
