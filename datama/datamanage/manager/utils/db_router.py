# utils/db_router.py
from django.db import connections
from django.db.utils import ConnectionDoesNotExist

def setup_target_db(alias: str, config: dict):
    """
    动态添加目标数据库配置到 Django connections
    alias: 数据库别名，例如 "target_db"
    config: dict 包含数据库连接参数
    """
    from django.conf import settings

    settings.DATABASES[alias] = {
        "ENGINE": "django.db.backends.mysql",
        "NAME": config["NAME"],
        "USER": config["USER"],
        "PASSWORD": config["PASSWORD"],
        "HOST": config["HOST"],
        "PORT": config.get("PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }

    # 清理旧连接，避免复用
    if alias in connections.databases:
        try:
            connections[alias].close()
        except ConnectionDoesNotExist:
            pass
