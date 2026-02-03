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

class SchedulerStatus(BaseModel):
    """调度器状态响应"""
    running: bool
    tasks_count: int
    active_tasks: List[str]
