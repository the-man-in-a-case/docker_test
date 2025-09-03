from django.db import models
import uuid

class Task(models.Model):
    """任务模型（Worker端）"""
    TASK_STATUS_CHOICES = (
        ('PENDING', '待处理'),
        ('PROCESSING', '处理中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_name = models.CharField(max_length=255)
    task_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='PENDING')
    input_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    celery_task_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False  # 不创建表，仅用于查询
        db_table = 'taskmanager_task'

class TaskResult(models.Model):
    """任务结果模型（Worker端）"""
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='result')
    result_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False  # 不创建表，仅用于查询
        db_table = 'taskmanager_taskresult'