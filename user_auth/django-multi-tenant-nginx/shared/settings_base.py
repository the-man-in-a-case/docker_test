import os
from decouple import config
from datetime import timedelta

SECRET_KEY = config('DJANGO_SECRET', default='e1%whp(q2u#bu8scs$jf4cobp*s25o81fg_02d%w9vxbt-^g5_')
DEBUG = config('DJANGO_DEBUG', cast=bool, default=False)
ALLOWED_HOSTS = ['*']

AUTH_USER_MODEL = 'shared.User'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'shared',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'shared.middleware.UpdateLastAccessMiddleware',
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DB', default='tenants'),
        'USER': config('MYSQL_USER', default='tenants'),
        'PASSWORD': config('MYSQL_PASSWORD', default='tenants_pass'),
        'HOST': config('MYSQL_HOST', default='mysql'),
        'PORT': config('MYSQL_PORT', default='3306'),
        'CONN_MAX_AGE': 60,
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": config('JWT_SECRET', default='jwt-secret'),
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}


JWT_SECRET = config('JWT_SECRET', default='jwt-secret')
ROUTE_SIGNING_SECRET = config('ROUTE_SIGNING_SECRET', default='route-sign')
TIME_ZONE = 'Asia/Taipei'
USE_TZ = True

# K8s
K8S_IN_CLUSTER = config('K8S_IN_CLUSTER', cast=bool, default=True)
DEFAULT_USER_NS = config('DEFAULT_USER_NS', default='tenant-a')  # 可与多命名空间匹配
K8S_DOMAIN_SUFFIX = config('K8S_DOMAIN_SUFFIX', default='svc.cluster.local')

# Celery（若在 Manager 使用）
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/1')
