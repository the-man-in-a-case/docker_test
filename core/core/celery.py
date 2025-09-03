import os
from celery import Celery

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# 初始化Celery
app = Celery('worker')

# 从设置文件中加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks(['tasks'])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')