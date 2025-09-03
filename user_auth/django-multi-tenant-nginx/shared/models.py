# from django.db import models

# class TenantUser(models.Model):
#     username = models.CharField(max_length=64, unique=True)
#     # 简化起见，仍保留 token 字段；生产用 JWT（此字段可作为旧 token 或互操作用途）
#     # token = models.CharField(max_length=256, unique=True)
#     token = models.CharField(
#         max_length=255,  # 改为 255 或更小
#         unique=True,
#         verbose_name="Token"
#     )
#     # 多命名空间支持：每用户资源所在 ns
#     namespace = models.CharField(max_length=63, default='tenant-a')
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_access_at = models.DateTimeField(null=True, blank=True)  # 用于回收策略

#     def __str__(self):
#         return f"{self.username}({self.id})"

# shared/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

ROLE_CHOICES = (
    ('admin', 'Admin'),
    ('tenant', 'Tenant'),
)

class User(AbstractUser):
    # 补充业务必需字段
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default='tenant')
    namespace = models.CharField(max_length=63, default='tenant-a')
    last_access_at = models.DateTimeField(null=True, blank=True)

    # 兼容旧逻辑：若你仍有历史 token 互操作，可临时保留
    legacy_token = models.CharField(max_length=256, null=True, blank=True, unique=True)

    def __str__(self):
        return f"{self.username}({self.id})"
