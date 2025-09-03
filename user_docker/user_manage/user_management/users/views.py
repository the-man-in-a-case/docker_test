from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import UserSerializer, UserCreateSerializer
from kubernetes_integration.tasks import create_user_resources, delete_user_resources

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 异步创建Kubernetes资源
        create_user_resources.delay(str(user.id))
        
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user_id = str(user.id)
        
        # 先删除用户，然后异步删除Kubernetes资源
        response = super().destroy(request, *args, **kwargs)
        
        # 异步删除Kubernetes资源
        delete_user_resources.delay(user_id)
        
        return response

    @action(detail=True, methods=['post'])
    def sync_resources(self, request, pk=None):
        """手动同步Kubernetes资源"""
        user = self.get_object()
        create_user_resources.delay(str(user.id))
        return Response({'status': 'sync started'})

    @action(detail=True, methods=['get'])
    def resource_status(self, request, pk=None):
        """获取用户Kubernetes资源状态"""
        user = self.get_object()
        from kubernetes_integration.utils import get_user_resource_status
        status = get_user_resource_status(str(user.id))
        return Response(status)


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy'})