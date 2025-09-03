from shared.settings_base import *
INSTALLED_APPS += ['authsvc', 'django.contrib.sessions']
ROOT_URLCONF = 'authsvc.urls'
WSGI_APPLICATION = 'authsvc.wsgi.application'

# 添加 Redis 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'auth_service',
        'TIMEOUT': 300,  # 默认缓存时间 5 分钟
    },
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL_SESSION', default='redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'auth_session',
        'TIMEOUT': 3600,  # 会话缓存时间 1 小时
    }
}
# 使用 Redis 作为会话存储
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'

# 添加缓存中间件
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',  # 添加缓存中间件
    'django.middleware.cache.FetchFromCacheMiddleware',  # 添加缓存中间件
    'shared.middleware.UpdateLastAccessMiddleware',
]

# 缓存设置
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300  # 5 分钟
CACHE_MIDDLEWARE_KEY_PREFIX = 'auth_service'

# Redis 连接池配置
REDIS_CONNECTION_POOL = {
    'max_connections': 50,
    'retry_on_timeout': True,
    'socket_keepalive': True,
    'socket_keepalive_options': {},
}

# 缓存键前缀
CACHE_KEY_PREFIX = 'auth_service'

# 添加日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.cache': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}