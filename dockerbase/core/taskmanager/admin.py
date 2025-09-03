from django.contrib import admin
from .models import Task, TaskResult


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # 列表页面显示的字段
    list_display = ('id', 'task_name', 'task_type', 'status', 'priority', 'created_at', 'updated_at')
    # 搜索字段
    search_fields = ('task_name', 'task_type', 'status')
    # 过滤字段
    list_filter = ('task_type', 'status', 'priority')
    # 字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('task_name', 'task_type', 'status', 'priority')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
        ('其他信息', {
            'fields': ('description', 'user_id')
        })
    )
    # 只读字段
    readonly_fields = ('created_at', 'updated_at')
    # 每页显示数量
    list_per_page = 20


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    # 列表页面显示的字段
    list_display = ('id', 'task', 'status', 'result_data', 'created_at')
    # 搜索字段
    search_fields = ('task__task_name', 'status')
    # 过滤字段
    list_filter = ('status', 'created_at')
    # 字段分组
    fieldsets = (
        ('任务信息', {
            'fields': ('task', 'status')
        }),
        ('结果数据', {
            'fields': ('result_data',)
        }),
        ('时间信息', {
            'fields': ('created_at',)
        })
    )
    # 只读字段
    readonly_fields = ('created_at',)
    # 每页显示数量
    list_per_page = 20