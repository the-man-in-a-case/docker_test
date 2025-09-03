from django.db import models
import uuid

class Task(models.Model):
    """任务模型，用于存储提交的任务信息"""
    TASK_STATUS_CHOICES = (
        ('PENDING', '待处理'),
        ('PROCESSING', '处理中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_name = models.CharField(max_length=255, verbose_name='任务名称')
    task_type = models.CharField(max_length=100, verbose_name='任务类型')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='PENDING', verbose_name='任务状态')
    input_data = models.JSONField(verbose_name='输入数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    celery_task_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Celery任务ID')

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务管理'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task_name} ({self.get_status_display()})'


class TaskResult(models.Model):
    """任务结果模型，用于存储任务执行结果"""
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='result', verbose_name='关联任务')
    result_data = models.JSONField(blank=True, null=True, verbose_name='结果数据')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='完成时间')

    class Meta:
        verbose_name = '任务结果'
        verbose_name_plural = '任务结果管理'

    def __str__(self):
        return f'{self.task.task_name}的结果'