from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
# from shared.models import TenantUser
from django.contrib.auth import get_user_model
User = get_user_model()
from .tasks import ensure_user_stack_task, delete_user_stack_task

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        ensure_user_stack_task.delay(instance.id)

@receiver(post_delete, sender=User)
def on_user_deleted(sender, instance, **kwargs):
    delete_user_stack_task.delay(instance.id, instance.namespace)
