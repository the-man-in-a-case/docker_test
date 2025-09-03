import os

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE', 'default_db'),
        'USER': os.environ.get('MYSQL_USER', 'default_user'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', 'default_password'),
        'HOST': os.environ.get('MYSQL_HOST', 'mysql'),
        'PORT': os.environ.get('MYSQL_PORT', '3306'),
    }
}

# Celery配置
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'db+mysql://{0}:{1}@{2}:{3}/{4}'.format(
    os.environ.get('MYSQL_USER', 'default_user'),
    os.environ.get('MYSQL_PASSWORD', 'default_password'),
    os.environ.get('MYSQL_HOST', 'mysql'),
    os.environ.get('MYSQL_PORT', '3306'),
    os.environ.get('MYSQL_DATABASE', 'default_db')
))
CELERY_TIMEZONE = os.environ.get('CELERY_TIMEZONE', 'Asia/Shanghai')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600

# Redis配置（用于缓存）
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')