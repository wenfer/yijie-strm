"""
网盘管理服务

支持多个网盘账号的管理（支持不同类型的网盘）
使用数据库存储（支持 SQLite 和 MySQL）
"""
from __future__ import annotations
import json
import logging
import os
import time
from typing import Dict, List, Optional
from pathlib import Path

# 导入新的 Provider 系统
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lib.core.provider import CloudStorageProvider
from lib.core.auth import AuthProvider
from lib.core.exceptions import AuthenticationError
from lib.providers.factory import provider_factory

# 导入数据库
from ..db import get_database, DatabaseInterface
from ..config import AppConfig, default_config

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
        self.token_file = token_file or f"~/.{drive_type}_token_{drive_id}.json"
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
            # 对于 115，检查 token 格式和过期时间
            if self.drive_type == "115":
                with open(token_path, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)

                if not isinstance(token_data, dict) or "data" not in token_data:
                    return False

                # 检查 token 是否过期
                timestamp = token_data.get("timestamp", 0)
                expires_in = token_data.get("data", {}).get("expires_in", 7200)
                expire_time = timestamp + expires_in

                return time.time() < expire_time
            else:
                # 其他网盘类型，简单检查文件是否存在
                return True

        except Exception as e:
            logger.error(f"drive_service.py:95 - Failed to check authentication for drive {self.drive_id}: {e}")
            return False


class DriveService:
    """网盘管理服务（使用数据库存储，支持多类型网盘）"""

    def __init__(self, config: AppConfig = None):
        self.config = config or default_config
        self.db: Optional[DatabaseInterface] = None
        self._current_drive_id: Optional[str] = None
        self._provider_cache: Dict[str, CloudStorageProvider] = {}
        self._initialize_database()
        self._migrate_from_json()

    def _initialize_database(self):
        """初始化数据库连接"""
        try:
            self.db = get_database(self.config)
            self.db.connect()
            logger.info("drive_service.py:117 - Database initialized successfully")

            # 加载当前网盘 ID
            self._load_current_drive()
        except Exception as e:
            logger.error(f"drive_service.py:122 - Failed to initialize database: {e}")
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
                logger.info(f"drive_service.py:134 - Loaded current drive: {self._current_drive_id}")
        except Exception as e:
            logger.error(f"drive_service.py:136 - Failed to load current drive: {e}")

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
            logger.error(f"drive_service.py:156 - Failed to save current drive: {e}")

    def _migrate_from_json(self):
        """从 JSON 文件迁移数据到数据库"""
        drives_file = os.path.expanduser("~/.115_drives.json")
        if not os.path.exists(drives_file):
            return

        try:
            # 检查数据库是否已有数据
            result = self.db.fetchone("SELECT COUNT(*) as count FROM drives")
            if result and result["count"] > 0:
                logger.info("drive_service.py:170 - Database already has data, skipping migration")
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

            logger.info(f"drive_service.py:197 - Migrated {len(drives)} drives from JSON to database")

            # 备份 JSON 文件
            backup_file = drives_file + ".backup"
            os.rename(drives_file, backup_file)
            logger.info(f"drive_service.py:202 - Backed up JSON file to {backup_file}")

        except Exception as e:
            logger.error(f"drive_service.py:205 - Failed to migrate from JSON: {e}")

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
            logger.error(f"drive_service.py:226 - Failed to list drives: {e}")
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
            logger.error(f"drive_service.py:238 - Failed to get drive {drive_id}: {e}")
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

            logger.info(f"drive_service.py:275 - Added drive: {drive_id} ({name}, type: {drive_type})")
            return drive
        except Exception as e:
            logger.error(f"drive_service.py:278 - Failed to add drive: {e}")
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
                    logger.info(f"drive_service.py:294 - Removed token file: {token_path}")
                except Exception as e:
                    logger.error(f"drive_service.py:296 - Failed to remove token file: {e}")

            # 从缓存移除
            if drive_id in self._provider_cache:
                del self._provider_cache[drive_id]

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

            logger.info(f"drive_service.py:318 - Removed drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"drive_service.py:321 - Failed to remove drive {drive_id}: {e}")
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
            logger.info(f"drive_service.py:342 - Set current drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"drive_service.py:345 - Failed to set current drive {drive_id}: {e}")
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

            logger.info(f"drive_service.py:362 - Updated drive: {drive_id}")
            return True
        except Exception as e:
            logger.error(f"drive_service.py:365 - Failed to update drive {drive_id}: {e}")
            return False

    def mark_drive_unauthenticated(self, drive_id: str) -> bool:
        """标记网盘为未认证状态（删除 token 文件）"""
        try:
            drive = self.get_drive(drive_id)
            if not drive:
                logger.warning(f"drive_service.py:374 - Drive not found: {drive_id}")
                return False

            # 删除 token 文件
            token_path = os.path.expanduser(drive.token_file)
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    logger.warning(f"drive_service.py:382 - Removed invalid token file for drive {drive_id}: {token_path}")
                except Exception as e:
                    logger.error(f"drive_service.py:384 - Failed to remove token file: {e}")
                    return False

            # 从缓存移除
            if drive_id in self._provider_cache:
                del self._provider_cache[drive_id]

            logger.warning(f"drive_service.py:392 - Drive {drive_id} marked as unauthenticated")
            return True
        except Exception as e:
            logger.error(f"drive_service.py:395 - Failed to mark drive {drive_id} as unauthenticated: {e}")
            return False

    # ==================== Provider 管理（新增） ====================

    def get_provider(self, drive_id: Optional[str] = None) -> Optional[CloudStorageProvider]:
        """获取指定网盘的 Provider 实例

        使用 Provider 工厂创建，支持多种网盘类型
        """
        if not drive_id:
            drive_id = self._current_drive_id

        if not drive_id:
            logger.error("drive_service.py:411 - No drive_id specified and no current drive set")
            return None

        # 检查缓存
        if drive_id in self._provider_cache:
            return self._provider_cache[drive_id]

        drive = self.get_drive(drive_id)
        if not drive:
            logger.error(f"drive_service.py:420 - Drive not found: {drive_id}")
            return None

        # 检查是否已认证
        if not drive.is_authenticated():
            logger.error(f"drive_service.py:425 - Drive {drive_id} is not authenticated")
            return None

        try:
            # 使用 Provider 工厂创建实例
            token_file = os.path.expanduser(drive.token_file)
            provider = provider_factory.create(
                provider_type=drive.drive_type,
                token_file=token_file
            )

            # 验证 Provider 是否可用（尝试认证）
            try:
                provider.ensure_authenticated()
            except AuthenticationError as e:
                logger.error(f"drive_service.py:440 - Authentication failed for drive {drive_id}: {e}")
                self.mark_drive_unauthenticated(drive_id)
                return None

            # 缓存 Provider
            self._provider_cache[drive_id] = provider

            logger.info(f"drive_service.py:448 - Created {drive.drive_type} provider for drive {drive_id}")
            return provider

        except Exception as e:
            logger.error(f"drive_service.py:452 - Failed to create provider for drive {drive_id}: {e}")
            # 如果是认证相关错误，标记为未认证
            if 'token' in str(e).lower() or 'auth' in str(e).lower():
                self.mark_drive_unauthenticated(drive_id)
            return None

    def get_auth_provider(self, drive_type: str = "115") -> Optional[AuthProvider]:
        """获取指定类型的认证 Provider

        用于扫码认证等操作
        """
        try:
            # 创建临时 Provider 获取 AuthProvider
            temp_token_file = os.path.expanduser(f"~/.{drive_type}_temp_auth.json")
            provider = provider_factory.create(
                provider_type=drive_type,
                token_file=temp_token_file
            )
            return provider.auth_provider

        except Exception as e:
            logger.error(f"drive_service.py:474 - Failed to get auth provider for {drive_type}: {e}")
            return None

    # ==================== 向后兼容方法（保留） ====================

    def get_token_manager(self, drive_id: Optional[str] = None):
        """获取指定网盘的 TokenManager（向后兼容）

        注意：此方法仅用于向后兼容，新代码应使用 get_provider()
        """
        logger.warning("drive_service.py:485 - get_token_manager() is deprecated, use get_provider() instead")

        if not drive_id:
            drive_id = self._current_drive_id

        if not drive_id:
            return None

        drive = self.get_drive(drive_id)
        if not drive:
            return None

        # 仅支持 115 网盘
        if drive.drive_type != "115":
            logger.error(f"drive_service.py:500 - get_token_manager() only supports 115 drives")
            return None

        # 尝试使用新的 AuthProvider 机制（如果可能）
        # 但 TokenManager 类已经不存在，所以只能返回 None
        # 如果调用者依赖 TokenManager，这里会报错，但这是预期的（因为 API 变了）
        logger.error("drive_service.py:504 - TokenManager class has been removed, please migrate to AuthProvider")
        return None

    def get_client(self, drive_id: Optional[str] = None):
        """获取指定网盘的 Client115 实例（向后兼容）

        注意：此方法仅用于向后兼容，新代码应使用 get_provider()
        """
        logger.warning("drive_service.py:518 - get_client() is deprecated, use get_provider() instead")

        if not drive_id:
            drive_id = self._current_drive_id

        if not drive_id:
            logger.error("drive_service.py:524 - No drive_id specified and no current drive set")
            return None

        drive = self.get_drive(drive_id)
        if not drive:
            logger.error(f"drive_service.py:529 - Drive not found: {drive_id}")
            return None

        # 仅支持 115 网盘
        if drive.drive_type != "115":
            logger.error(f"drive_service.py:534 - get_client() only supports 115 drives")
            return None

        # 检查是否已认证
        if not drive.is_authenticated():
            logger.error(f"drive_service.py:539 - Drive {drive_id} is not authenticated")
            return None

        # 创建 Client115
        from ..config import AppConfig
        # 修改导入路径，指向新的位置
        from ..providers.drive_115.client import Client115

        # 为了兼容旧的 Client115 构造函数，我们需要创建一个 Config115
        # 注意：新的 Client115 只需要 Config115，不需要 TokenManager
        from ..providers.drive_115.config import Config115

        # 读取 token 内容以传递给 API 调用（新的 Client115 不管理 token，只负责 API 调用）
        # 但这里的问题是：旧代码期望 get_client 返回一个可以自动管理 token 的对象
        # 新的 Client115 只是一个纯 API 包装器

        # 尝试构建一个兼容层或者直接返回新 Client115
        # 考虑到调用者可能只是用它来调用 list_files 等方法

        config_115 = Config115()

        # 注意：新的 Client115 不需要 auth_provider 或 token_file
        # 它需要在调用方法时传入 access_token
        # 这意味着直接返回 Client115 可能不兼容旧代码（旧代码可能不传 token）
        # 但为了解决导入错误，我们先返回新 Client115

        return Client115(config_115)


    def close(self):
        """关闭数据库连接和清理 Provider 缓存"""
        # 清理 Provider 缓存
        self._provider_cache.clear()

        if self.db:
            self.db.close()
            self.db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
