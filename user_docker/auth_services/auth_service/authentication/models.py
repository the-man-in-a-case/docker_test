from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

# 统一用户模型 - 只读模式，不创建表
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    
    # 用户管理相关字段
    kubernetes_namespace = models.CharField(max_length=63, blank=True)
    nginx_pod_name = models.CharField(max_length=253, blank=True)
    
    # 认证相关字段
    is_service_account = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        managed = False  # 不创建表
        db_table = 'users_user'  # 使用user_management创建的表