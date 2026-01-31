"""
通用数据模型

定义跨网盘的统一数据结构
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class FileType(Enum):
    """文件类型枚举"""
    FOLDER = "folder"
    FILE = "file"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    OTHER = "other"


class EventType(Enum):
    """文件事件类型"""
    UPLOAD = "upload"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    CREATE_FOLDER = "create_folder"
    COPY = "copy"
    SHARE = "share"
    UNKNOWN = "unknown"


@dataclass
class FileItem:
    """统一文件项模型

    抽象不同网盘的文件表示
    """
    # 核心字段
    id: str                          # 文件唯一标识符（通用）
    name: str                        # 文件名
    type: FileType                   # 文件类型
    size: int                        # 文件大小（字节）
    parent_id: str                   # 父目录 ID

    # 可选字段
    path: Optional[str] = None       # 完整路径
    created_at: Optional[float] = None   # 创建时间（Unix 时间戳）
    modified_at: Optional[float] = None  # 修改时间

    # 下载相关
    download_id: Optional[str] = None    # 下载标识符（如 115 的 pick_code）

    # 扩展字段（保存原始数据）
    raw_data: Optional[Dict[str, Any]] = None

    @property
    def is_folder(self) -> bool:
        """是否是文件夹"""
        return self.type == FileType.FOLDER

    @property
    def is_video(self) -> bool:
        """是否是视频文件"""
        return self.type == FileType.VIDEO

    @property
    def is_audio(self) -> bool:
        """是否是音频文件"""
        return self.type == FileType.AUDIO


@dataclass
class FileEvent:
    """文件变更事件"""
    event_id: str                    # 事件 ID
    event_type: EventType            # 事件类型
    file_id: str                     # 文件 ID
    file_name: str                   # 文件名
    parent_id: str                   # 父目录 ID
    timestamp: float                 # 事件时间戳

    # 可选字段
    old_parent_id: Optional[str] = None  # 移动前的父目录
    old_name: Optional[str] = None       # 重命名前的名称

    # 扩展字段
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class AuthToken:
    """认证令牌"""
    access_token: str                # 访问令牌
    refresh_token: Optional[str] = None  # 刷新令牌
    expires_at: Optional[float] = None   # 过期时间（Unix 时间戳）
    token_type: str = "Bearer"       # 令牌类型

    # 扩展字段（保存原始数据）
    raw_data: Optional[Dict[str, Any]] = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """检查令牌是否过期

        Args:
            buffer_seconds: 提前多少秒判定为过期（默认 60 秒）
        """
        if self.expires_at is None:
            return False

        import time
        return time.time() >= (self.expires_at - buffer_seconds)


@dataclass
class QRCodeAuth:
    """二维码认证信息"""
    qrcode_url: str                  # 二维码图片 URL
    session_id: str                  # 会话 ID（用于轮询）
    expires_at: float                # 二维码过期时间

    # 扩展字段
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class DriveInfo:
    """网盘信息"""
    drive_id: str                    # 网盘 ID
    drive_type: str                  # 网盘类型（115/aliyun/baidu 等）
    name: str                        # 显示名称
    user_id: Optional[str] = None    # 用户 ID
    space_total: Optional[int] = None    # 总空间（字节）
    space_used: Optional[int] = None     # 已用空间（字节）

    # 扩展字段
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class DownloadInfo:
    """下载信息"""
    url: str                         # 下载 URL
    expires_at: Optional[float] = None   # 过期时间
    headers: Optional[Dict[str, str]] = None  # 请求头

    # 扩展字段
    raw_data: Optional[Dict[str, Any]] = None
