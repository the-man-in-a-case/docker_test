from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .permissions import IsAdmin, AdminOrTenantReadCreate

User = get_user_model()

class UserAdminViewSet(ModelViewSet):
    """
    管理员：用户全量管理（数据库操作权限/业务管理 API）
    """
    queryset = User.objects.all()
    serializer_class = None  # 省略：请按需补 DRF Serializer
    permission_classes = [IsAdmin]

class TaskViewSet(ModelViewSet):
    """
    任务 API（示例）：
    - admin：全权限
    - tenant：仅 GET（查看数据）与 POST（创建任务）
    """
    queryset = []  # 你的任务模型
    serializer_class = None
    permission_classes = [AdminOrTenantReadCreate]

    def create(self, request, *args, **kwargs):
        # tenant 可创建
        return Response({"ok": True}, status=201)
