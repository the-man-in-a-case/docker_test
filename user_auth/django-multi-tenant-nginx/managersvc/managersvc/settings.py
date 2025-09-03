from shared.settings_base import *
INSTALLED_APPS += ['managersvc', 'users']
ROOT_URLCONF = 'managersvc.urls'
WSGI_APPLICATION = 'managersvc.wsgi.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'managersvc.middleware.HealthCheckLogMiddleware',
    'shared.middleware.TenantMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from celery.schedules import crontab
# 配置周期性任务
app.conf.beat_schedule = {
    'scale-idle-users': {
        'task': 'users.tasks.scale_idle_users_task',  # 对应 tasks.py 中的函数
        'schedule': crontab(minute='*/10'),  # 每 10 分钟执行一次
        # 也可以用 crontab，例如每分钟执行一次：
        # 'schedule': crontab(minute='*'),
        'args': (60,)  # 传递给任务的参数
    },
    # 更多任务示例：
    # 'daily-report': {
    #     'task': 'tasks.daily_backup',
    #     'schedule': crontab(hour=2, minute=0),  # 每天凌晨 2 点
    # }
}
