"""
任务数据模型
"""
from enum import Enum
from tortoise import fields
from tortoise.models import Model


class TaskStatus(str, Enum):
    """任务状态"""
    IDLE = "idle"           # 空闲
    PENDING = "pending"     # 等待执行
    RUNNING = "running"     # 执行中
    SUCCESS = "success"     # 成功
    ERROR = "error"         # 失败


class ScheduleType(str, Enum):
    """调度类型"""
    INTERVAL = "interval"   # 间隔执行
    CRON = "cron"           # Cron 表达式
    MANUAL = "manual"       # 手动执行


class StrmTask(Model):
    """STRM 生成任务模型"""
    
    # 任务 ID
    id = fields.CharField(max_length=64, pk=True, description="任务ID")
    
    # 任务名称
    name = fields.CharField(max_length=255, description="任务名称")
    
    # 关联网盘
    drive = fields.ForeignKeyField(
        "models.Drive",
        related_name="tasks",
        on_delete=fields.CASCADE,
        description="关联网盘"
    )
    
    # 源文件夹 CID
    source_cid = fields.CharField(max_length=64, description="源文件夹CID")
    
    # 输出目录
    output_dir = fields.CharField(max_length=500, description="输出目录")
    
    # STRM 基础 URL
    base_url = fields.CharField(max_length=500, null=True, description="STRM基础URL")
    
    # 文件过滤配置
    include_video = fields.BooleanField(default=True, description="包含视频")
    include_audio = fields.BooleanField(default=False, description="包含音频")
    custom_extensions = fields.JSONField(null=True, description="自定义扩展名")
    
    # 调度配置
    schedule_enabled = fields.BooleanField(default=False, description="启用调度")
    schedule_type = fields.CharField(max_length=20, null=True, description="调度类型")
    schedule_config = fields.JSONField(null=True, description="调度配置")
    
    # 监听配置
    watch_enabled = fields.BooleanField(default=False, description="启用监听")
    watch_interval = fields.IntField(default=1800, description="监听间隔(秒)")
    
    # 同步选项
    delete_orphans = fields.BooleanField(default=True, description="删除孤立文件")
    preserve_structure = fields.BooleanField(default=True, description="保留目录结构")
    overwrite_strm = fields.BooleanField(default=False, description="覆盖已有STRM")
    
    # 状态信息
    status = fields.CharField(max_length=20, default="idle", description="状态")
    last_run_time = fields.DatetimeField(null=True, description="上次运行时间")
    last_run_status = fields.CharField(max_length=20, null=True, description="上次运行状态")
    last_run_message = fields.TextField(null=True, description="上次运行消息")
    next_run_time = fields.DatetimeField(null=True, description="下次运行时间")
    
    # 统计信息
    total_runs = fields.IntField(default=0, description="总运行次数")
    total_files_generated = fields.IntField(default=0, description="生成文件总数")
    
    # 进度信息
    total_files = fields.IntField(default=0, description="文件总数")
    current_file_index = fields.IntField(default=0, description="当前文件索引")
    
    # 事件监听
    last_event_id = fields.IntField(default=0, description="最后事件ID")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "strm_tasks"
        table_description = "STRM生成任务表"
    
    def __str__(self) -> str:
        return f"StrmTask({self.id}: {self.name})"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "drive_id": self.drive_id,
            "source_cid": self.source_cid,
            "output_dir": self.output_dir,
            "base_url": self.base_url,
            "include_video": self.include_video,
            "include_audio": self.include_audio,
            "custom_extensions": self.custom_extensions,
            "schedule_enabled": self.schedule_enabled,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "watch_enabled": self.watch_enabled,
            "watch_interval": self.watch_interval,
            "delete_orphans": self.delete_orphans,
            "preserve_structure": self.preserve_structure,
            "overwrite_strm": self.overwrite_strm,
            "status": self.status,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_run_status": self.last_run_status,
            "last_run_message": self.last_run_message,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "total_runs": self.total_runs,
            "total_files_generated": self.total_files_generated,
            "total_files": self.total_files,
            "current_file_index": self.current_file_index,
            "last_event_id": self.last_event_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class StrmRecord(Model):
    """STRM 文件记录模型"""
    
    # 记录 ID
    id = fields.CharField(max_length=128, pk=True, description="记录ID")
    
    # 关联任务
    task = fields.ForeignKeyField(
        "models.StrmTask",
        related_name="records",
        on_delete=fields.CASCADE,
        description="关联任务"
    )
    
    # 文件信息
    file_id = fields.CharField(max_length=64, description="文件ID")
    pick_code = fields.CharField(max_length=64, null=True, description="PickCode")
    file_name = fields.CharField(max_length=500, description="文件名")
    file_size = fields.BigIntField(null=True, description="文件大小")
    file_path = fields.CharField(max_length=1000, description="文件路径")
    
    # STRM 文件信息
    strm_path = fields.CharField(max_length=1000, description="STRM文件路径")
    strm_content = fields.TextField(description="STRM文件内容")
    
    # 状态：active, deleted
    status = fields.CharField(max_length=20, default="active", description="状态")
    
    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    
    class Meta:
        table = "strm_records"
        table_description = "STRM文件记录表"
    
    def __str__(self) -> str:
        return f"StrmRecord({self.id}: {self.file_name})"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "file_id": self.file_id,
            "pick_code": self.pick_code,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_path": self.file_path,
            "strm_path": self.strm_path,
            "strm_content": self.strm_content,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaskLog(Model):
    """任务执行日志模型"""
    
    # 日志 ID
    id = fields.CharField(max_length=128, pk=True, description="日志ID")
    
    # 关联任务
    task = fields.ForeignKeyField(
        "models.StrmTask",
        related_name="logs",
        on_delete=fields.CASCADE,
        description="关联任务"
    )
    
    # 执行时间
    start_time = fields.DatetimeField(auto_now_add=True, description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    duration = fields.FloatField(null=True, description="执行时长(秒)")
    
    # 执行状态
    status = fields.CharField(max_length=20, description="状态")
    message = fields.TextField(null=True, description="消息")
    error_trace = fields.TextField(null=True, description="错误堆栈")
    
    # 执行统计
    files_scanned = fields.IntField(default=0, description="扫描文件数")
    files_added = fields.IntField(default=0, description="新增文件数")
    files_updated = fields.IntField(default=0, description="更新文件数")
    files_deleted = fields.IntField(default=0, description="删除文件数")
    files_skipped = fields.IntField(default=0, description="跳过文件数")
    
    class Meta:
        table = "task_logs"
        table_description = "任务执行日志表"
    
    def __str__(self) -> str:
        return f"TaskLog({self.id}: {self.status})"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status,
            "message": self.message,
            "error_trace": self.error_trace,
            "files_scanned": self.files_scanned,
            "files_added": self.files_added,
            "files_updated": self.files_updated,
            "files_deleted": self.files_deleted,
            "files_skipped": self.files_skipped,
        }
