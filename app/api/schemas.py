"""
API 数据模型 (Pydantic)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 通用响应 ====================

class ResponseBase(BaseModel):
    """基础响应"""
    success: bool = True
    message: Optional[str] = None


class DataResponse(ResponseBase):
    """数据响应"""
    data: Optional[Any] = None


class ListResponse(ResponseBase):
    """列表响应"""
    items: List[Any] = []
    total: int = 0


# ==================== 配置相关 ====================

class GatewayConfig(BaseModel):
    """网关配置"""
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8115, description="监听端口")
    debug: bool = Field(default=False, description="调试模式")
    strm_base_url: Optional[str] = Field(None, description="STRM 文件基础 URL")
    cache_ttl: int = Field(default=3600, description="下载链接缓存时间(秒)")
    enable_cors: bool = Field(default=True, description="启用 CORS")

class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = Field(..., description="数据库连接 URL")
    generate_schemas: bool = Field(default=True, description="自动生成表结构")
    pool_min: int = Field(default=1, description="最小连接池大小")
    pool_max: int = Field(default=10, description="最大连接池大小")

class LogConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s", description="日志格式")

class SystemConfig(BaseModel):
    """系统配置"""
    gateway: GatewayConfig
    database: DatabaseConfig
    log: LogConfig


# ==================== 网盘相关 ====================

class DriveCreate(BaseModel):
    """创建网盘请求"""
    name: str = Field(..., min_length=1, max_length=255, description="网盘名称")
    drive_type: str = Field(default="115", description="网盘类型")


class DriveUpdate(BaseModel):
    """更新网盘请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class DriveResponse(BaseModel):
    """网盘响应"""
    id: str
    name: str
    drive_type: str
    cookie_file: Optional[str]
    is_current: bool
    created_at: Optional[str]
    last_used: Optional[str]

    class Config:
        from_attributes = True


# ==================== 认证相关 ====================

class AuthExchange(BaseModel):
    """交换 Token 请求"""
    uid: str = Field(..., description="UID")
    code_verifier: str = Field(..., description="Code Verifier")
    drive_id: Optional[str] = Field(None, description="目标网盘 ID")


class AuthResponse(BaseModel):
    """认证响应"""
    drive_id: str
    access_token: str
    expires_in: int


# ==================== 文件相关 ====================

class FileItem(BaseModel):
    """文件项"""
    id: str
    name: str
    is_dir: bool
    size: int = 0
    parent_id: str
    pick_code: Optional[str] = None
    sha1: Optional[str] = None


class FileListResponse(ListResponse):
    """文件列表响应"""
    cid: str
    items: List[FileItem]


# ==================== 任务相关 ====================

class TaskCreate(BaseModel):
    """创建任务请求"""
    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    drive_id: str = Field(..., description="网盘 ID")
    source_cid: str = Field(..., description="源文件夹 CID")
    output_dir: str = Field(..., description="输出目录")
    base_url: Optional[str] = Field(None, description="STRM 基础 URL")

    # 文件过滤
    include_video: bool = Field(default=True, description="包含视频")
    include_audio: bool = Field(default=False, description="包含音频")
    custom_extensions: Optional[List[str]] = Field(None, description="自定义扩展名")

    # 调度配置
    schedule_enabled: bool = Field(default=False, description="启用调度")
    schedule_type: Optional[str] = Field(None, description="调度类型")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="调度配置")

    # 监听配置
    watch_enabled: bool = Field(default=False, description="启用监听")
    watch_interval: int = Field(default=1800, ge=60, description="监听间隔(秒)")

    # 同步选项
    delete_orphans: bool = Field(default=True, description="删除孤立文件")
    preserve_structure: bool = Field(default=True, description="保留目录结构")
    overwrite_strm: bool = Field(default=False, description="覆盖已有 STRM")
    download_metadata: bool = Field(default=False, description="下载刮削资源文件")


class TaskUpdate(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    source_cid: Optional[str] = None
    output_dir: Optional[str] = None
    base_url: Optional[str] = None
    include_video: Optional[bool] = None
    include_audio: Optional[bool] = None
    custom_extensions: Optional[List[str]] = None
    schedule_enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    watch_enabled: Optional[bool] = None
    watch_interval: Optional[int] = None
    delete_orphans: Optional[bool] = None
    preserve_structure: Optional[bool] = None
    overwrite_strm: Optional[bool] = None
    download_metadata: Optional[bool] = None


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    name: str
    drive_id: str
    source_cid: str
    output_dir: str
    base_url: Optional[str]
    include_video: bool
    include_audio: bool
    custom_extensions: Optional[List[str]]
    schedule_enabled: bool
    schedule_type: Optional[str]
    schedule_config: Optional[Dict[str, Any]]
    watch_enabled: bool
    watch_interval: int
    delete_orphans: bool
    preserve_structure: bool
    overwrite_strm: bool
    download_metadata: bool
    status: str
    last_run_time: Optional[str]
    last_run_status: Optional[str]
    last_run_message: Optional[str]
    next_run_time: Optional[str]
    total_runs: int
    total_files_generated: int
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class TaskExecute(BaseModel):
    """执行任务请求"""
    force: bool = Field(default=False, description="强制执行")


class TaskStatistics(BaseModel):
    """任务统计响应"""
    task_id: str
    task_name: str
    status: str
    total_runs: int
    total_files_generated: int
    active_records: int
    last_run_time: Optional[str]
    last_run_status: Optional[str]
    last_run_message: Optional[str]


# ==================== 调度器相关 ====================


# ==================== 挂载相关 ====================

class MountCreate(BaseModel):
    drive_id: str = Field(..., description="网盘ID")
    mount_point: str = Field(..., description="挂载点路径")
    mount_config: Optional[Dict[str, Any]] = Field(default={}, description="挂载配置")

class MountResponse(BaseModel):
    id: str
    drive_id: str
    mount_point: str
    mount_config: Dict[str, Any]
    is_mounted: bool
    created_at: float


# ==================== 云下载相关 ====================

class OfflineTaskStatus:
    """云下载任务状态"""
    PENDING = 0      # 等待下载
    DOWNLOADING = 1  # 下载中
    COMPLETED = 2    # 已完成
    FAILED = -1      # 失败
    UNKNOWN = 3      # 未知


class OfflineTaskItem(BaseModel):
    """云下载任务项"""
    info_hash: str = Field(..., description="任务哈希")
    name: str = Field(..., description="任务名称")
    size: int = Field(0, description="文件大小(字节)")
    size_formatted: str = Field("", description="格式化大小")
    status: int = Field(0, description="任务状态: 0=等待, 1=下载中, 2=已完成, -1=失败")
    status_text: str = Field("", description="状态文本")
    progress: float = Field(0.0, description="下载进度(0-100)")
    speed: int = Field(0, description="下载速度(字节/秒)")
    speed_formatted: str = Field("", description="格式化速度")
    create_time: int = Field(0, description="创建时间戳")
    create_time_formatted: str = Field("", description="格式化创建时间")
    update_time: int = Field(0, description="更新时间戳")
    update_time_formatted: str = Field("", description="格式化更新时间")
    save_cid: Optional[str] = Field(None, description="保存目录CID")
    url: Optional[str] = Field(None, description="下载链接")
    del_file: int = Field(0, description="是否删除源文件")


class OfflineListResponse(ResponseBase):
    """云下载任务列表响应"""
    page: int = Field(1, description="当前页码")
    per_page: int = Field(20, description="每页数量")
    total: int = Field(0, description="总任务数")
    tasks: List[OfflineTaskItem] = Field([], description="任务列表")


class OfflineAddUrlRequest(BaseModel):
    """添加云下载任务请求"""
    url: str = Field(..., description="下载链接(支持HTTP/HTTPS/磁力链/电驴等)")
    save_cid: Optional[str] = Field(None, description="保存到的文件夹CID")


class OfflineAddUrlsRequest(BaseModel):
    """批量添加云下载任务请求"""
    urls: List[str] = Field(..., description="下载链接列表")
    save_cid: Optional[str] = Field(None, description="保存到的文件夹CID")


class OfflineAddTorrentRequest(BaseModel):
    """添加种子云下载任务请求"""
    torrent_path: str = Field(..., description="种子文件路径")
    save_cid: Optional[str] = Field(None, description="保存到的文件夹CID")


class OfflineRemoveRequest(BaseModel):
    """删除云下载任务请求"""
    info_hashes: List[str] = Field(..., description="任务info_hash列表")


class OfflineRestartRequest(BaseModel):
    """重启云下载任务请求"""
    info_hash: str = Field(..., description="任务info_hash")


class OfflineClearRequest(BaseModel):
    """清空云下载任务请求"""
    status: int = Field(0, ge=0, le=2, description="0=已完成, 1=全部, 2=失败")


class OfflineQuotaInfo(BaseModel):
    """云下载配额信息"""
    total: int = Field(0, description="总配额(字节)")
    used: int = Field(0, description="已使用(字节)")
    remaining: int = Field(0, description="剩余(字节)")
    total_formatted: str = Field("", description="格式化总配额")
    used_formatted: str = Field("", description="格式化已使用")
    remaining_formatted: str = Field("", description="格式化剩余")


class OfflineTaskCount(BaseModel):
    """云下载任务数量统计"""
    total: int = Field(0, description="总任务数")
    downloading: int = Field(0, description="下载中")
    completed: int = Field(0, description="已完成")
    failed: int = Field(0, description="失败")
    pending: int = Field(0, description="等待中")


class OfflineDownloadPath(BaseModel):
    """云下载默认路径"""
    cid: str = Field("", description="文件夹CID")
    name: str = Field("", description="文件夹名称")
    path: str = Field("", description="完整路径")
