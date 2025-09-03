import os

# 基础配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = ['*']

# 应用定义
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'config',  # 当前配置目录
]


# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE', 'django_db'),
        'USER': os.environ.get('MYSQL_USER', 'admin'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', 'admin'),
        'HOST': os.environ.get('MYSQL_HOST', 'mysql-service.django-celery.svc.cluster.local'),
        'PORT': os.environ.get('MYSQL_PORT', '3306'),
    }
}
# Celery配置
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'amqp://admin:admin@rabbitmq-service.django-celery.svc.cluster.local:5672/')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis-service.django-celery.svc.cluster.local:6379/0')
CELERY_TIMEZONE = os.environ.get('CELERY_TIMEZONE', 'UTC')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Redis配置
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis-service.django-celery.svc.cluster.local')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')