import os
from celery import Celery

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 初始化Celery
app = Celery('core')

# 从设置文件中加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()