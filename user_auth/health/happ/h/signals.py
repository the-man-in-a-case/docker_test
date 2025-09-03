import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .k8s_ops import create_user_deployment, delete_user_deployment

User = get_user_model()

SIDE_CAR_IMAGE = getattr(settings, "SIDE_CAR_IMAGE", os.getenv("SIDE_CAR_IMAGE", "nginx-sidecar-detector:1.0"))
HEALTH_SERVICE_URL = getattr(settings, "HEALTH_SERVICE_URL", os.getenv(
    "HEALTH_SERVICE_URL", "http://health-service.your-namespace.svc.cluster.local:8080/report"))

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        create_user_deployment(instance.username, SIDE_CAR_IMAGE, HEALTH_SERVICE_URL)

@receiver(post_delete, sender=User)
def on_user_deleted(sender, instance, **kwargs):
    delete_user_deployment(instance.username)
