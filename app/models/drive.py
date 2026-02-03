"""
网盘数据模型
"""
from tortoise import fields
from tortoise.models import Model


class Drive(Model):
    """网盘账号模型"""
    
    # 主键：网盘 ID，格式: {type}_{timestamp}
    id = fields.CharField(max_length=64, pk=True, description="网盘ID")
    
    # 网盘名称
    name = fields.CharField(max_length=255, description="网盘名称")
    
    # 网盘类型：115, aliyun, etc.
    drive_type = fields.CharField(max_length=50, default="115", description="网盘类型")
    
    # Cookie 文件路径（p115client 使用）
    cookie_file = fields.CharField(max_length=500, null=True, description="Cookie文件路径")
    
    # 是否为当前默认网盘
    is_current = fields.BooleanField(default=False, description="是否为当前网盘")
    
    # 创建时间
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    
    # 最后使用时间
    last_used = fields.DatetimeField(auto_now=True, description="最后使用时间")
    
    class Meta:
        table = "drives"
        table_description = "网盘账号表"
    
    def __str__(self) -> str:
        return f"Drive({self.id}: {self.name})"
    
    def to_dict(self) -> dict:
        """转换为字典（兼容前端格式）"""
        import os
        
        # 检查是否已认证（cookie 文件存在且不为空）
        is_authenticated = False
        if self.cookie_file:
            try:
                is_authenticated = os.path.exists(self.cookie_file) and os.path.getsize(self.cookie_file) > 0
            except:
                pass
        
        return {
            "drive_id": self.id,  # 前端期望 drive_id
            "name": self.name,
            "drive_type": self.drive_type,
            "token_file": self.cookie_file,  # 前端期望 token_file
            "is_current": self.is_current,
            "is_authenticated": is_authenticated,  # 前端需要这个字段
            "created_at": int(self.created_at.timestamp()) if self.created_at else 0,  # 前端期望数字
            "last_used": int(self.last_used.timestamp()) if self.last_used else 0,  # 前端期望数字
        }
