import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "managersvc.settings"))
app = Celery("managersvc")
app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
app.autodiscover_tasks()
