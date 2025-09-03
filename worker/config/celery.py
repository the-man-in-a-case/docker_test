import os
import sys
from celery import Celery

# 设置项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 确保项目根目录在Python路径中
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 初始化Celery应用
app = Celery('worker')

# 从Django设置加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks(['tasks'])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')