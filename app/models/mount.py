from tortoise import fields, models

class Mount(models.Model):
    """
    FUSE 挂载点配置
    """
    id = fields.UUIDField(pk=True)
    drive = fields.ForeignKeyField('models.Drive', related_name='mounts')
    mount_point = fields.CharField(max_length=255, description="本地挂载目录")
    mount_config = fields.JSONField(default={}, description="挂载配置 (allow_other, etc.)")
    is_mounted = fields.BooleanField(default=False, description="是否已挂载")
    pid = fields.IntField(null=True, description="挂载进程ID")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "mounts"
        ordering = ["-created_at"]

    async def to_dict(self):
        # 确保 drive 关系已加载
        try:
            # 尝试获取 drive id，如果 drive 未加载会抛出 AttributeError
            drive_id = self.drive.id
        except AttributeError:
            await self.fetch_related('drive')
            drive_id = self.drive.id if self.drive else None

        return {
            "id": str(self.id),
            "drive_id": drive_id,
            "mount_point": self.mount_point,
            "mount_config": self.mount_config,
            "is_mounted": self.is_mounted,
            "created_at": self.created_at.timestamp() if self.created_at else 0
        }
