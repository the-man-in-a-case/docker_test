# models.py (新增/变更片段)
from django.conf import settings
from django.db import models
from db.models import Map, Layer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone  
from django.contrib.auth.models import User 


# === 新增：地图归档表（保存完整 JSON 快照） ===
class MapArchive(models.Model):
    """
    保存 Map 的固定版本快照（完整 JSON），用于精确回滚。
    """
    map = models.ForeignKey('db.Map', on_delete=models.CASCADE, related_name='archives')
    version_number = models.PositiveIntegerField(help_text='该快照对应的 Map 版本号')
    snapshot = models.JSONField(help_text='导出的 Map 完整 JSON（包含 layers）')
    author = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'MapArchive'
        verbose_name = '地图归档'
        verbose_name_plural = '地图归档'
        unique_together = ('map', 'version_number')  # 每个版本一个快照

    def __str__(self):
        return f"MapArchive map={self.map_id} v{self.version_number}"

# === 变更：导入任务，增加 user 与 logs ===
class ResourceImportJob(models.Model):
    IMPORT_TYPE_CHOICES = [
        ('MAP', 'Map全量导入'),
        ('LAYER', 'Layer增量导入')
    ]
    import_type = models.CharField(max_length=10, choices=IMPORT_TYPE_CHOICES)
    target_map = models.ForeignKey('db.Map', null=True, blank=True,
                                   on_delete=models.CASCADE, related_name='manager_import_jobs')
    target_layer = models.ForeignKey('db.Layer', null=True, blank=True,
                                     on_delete=models.CASCADE, related_name='manager_import_jobs')
    imported_data = models.JSONField(help_text='导入的JSON数据')
    status = models.CharField(max_length=20, default='PENDING',
                              choices=[('PENDING','待处理'), ('SUCCESS','成功'), ('FAILED','失败')])
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # 新增操作者 & 日志
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='resource_import_jobs')
    logs = models.JSONField(default=dict, blank=True, help_text='导入过程日志及差异快照')

    class Meta:
        verbose_name = '资源导入任务'
        verbose_name_plural = '资源导入任务'

    def __str__(self):
        return f"{self.get_import_type_display()} Import - {self.created_at}"

# === 新增：审计日志 ===
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('EXPORT', '导出'),
        ('IMPORT', '导入'),
        ('VERSION', '版本变更'),
        ('ROLLBACK', '回滚')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)  # 如 'Map', 'Layer'
    resource_id = models.IntegerField()
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'AuditLog'
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'

    def __str__(self):
        return f"AuditLog {self.action} {self.resource_type}#{self.resource_id}"


class MapVersionSnapshot(models.Model):
    from_map = models.ForeignKey(Map, on_delete=models.CASCADE, related_name='from_snapshots')
    to_map = models.ForeignKey(Map, on_delete=models.CASCADE, related_name='to_snapshots')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'MapVersionSnapshot'
        verbose_name = '地图版本快照'
        verbose_name_plural = '地图版本快照'
    
    def __str__(self):
        return f"Snapshot {self.id}: Map {self.from_map_id} -> {self.to_map_id}"



class LayerVersion(models.Model):
    """
    版本化: 每个 Layer 的快照数据（多版本）
    """
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    data = models.JSONField(encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("layer", "version")
        ordering = ["-version"]

    def __str__(self):
        return f"LayerVersion(layer={self.layer_id}, v{self.version})"