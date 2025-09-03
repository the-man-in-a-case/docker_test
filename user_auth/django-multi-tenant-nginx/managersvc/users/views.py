from django.shortcuts import render
from django.db import connection
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from kubernetes import client
from .k8s import ensure_stack, scale_stack
from .tasks import scale_up_user_deployment

# Create your views here.
@api_view(['GET'])
def health(request):
    """健康检查端点，返回服务状态"""
    try:
        # 检查数据库连接
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return Response({
            "status": "healthy",
            "service": "authsvc",
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "status": "unhealthy",
            "service": "authsvc",
            "error": str(e),
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)




class EnsureUserDeployment(APIView):
    permission_classes = [permissions.AllowAny]  # 走内部签名，不强制 JWT
    def post(self, request):
        user_id = request.data.get("user_id")
        namespace = request.data.get("namespace", "default")
        
        if not user_id:
            return Response({"error": "user_id required"}, status=400)

        config.load_incluster_config()
        apps_v1 = client.AppsV1Api()
        deploy_name = f"user-{user_id}-nginx"

        try:
            deploy = apps_v1.read_namespaced_deployment(
                name=deploy_name, namespace=namespace
            )
            replicas = deploy.spec.replicas
            
            if replicas is None:
                return Response(
                    {"status": "not_found", "message": "Deployment not found"}, 
                    status=404
                )
            elif replicas == 0:
                # 触发异步扩容
                scale_up_user_deployment.delay(user_id, namespace)
                return Response(
                    {"status": "scaling", "message": "User pod waking up"}, 
                    status=202
                )
            elif replicas > 0:
                return Response({"status": "ready"})
                
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return Response(
                    {"status": "not_found", "message": "Deployment not found"}, 
                    status=404
                )
            return Response({"error": str(e)}, status=500)