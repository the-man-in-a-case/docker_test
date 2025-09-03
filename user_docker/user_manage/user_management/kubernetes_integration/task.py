from celery import shared_task
from kubernetes_integration.utils import KubernetesManager
from users.models import User
import logging

logger = logging.getLogger(__name__)

@shared_task
def create_user_resources(user_id):
    """为用户创建Kubernetes资源"""
    try:
        user = User.objects.get(id=user_id)
        k8s = KubernetesManager()
        
        username = user.username
        
        # 创建Nginx部署
        deployment = k8s.create_user_nginx_deployment(user_id, username)
        user.nginx_pod_name = deployment.metadata.name
        
        # 创建Service
        service = k8s.create_user_service(user_id, username)
        user.nginx_service_name = service.metadata.name
        
        # 创建Ingress
        ingress = k8s.create_user_ingress(user_id, username)
        
        # 更新用户状态
        user.kubernetes_namespace = f"user-{user_id}"
        user.is_kubernetes_resources_created = True
        user.save()
        
        logger.info(f"Created Kubernetes resources for user {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create Kubernetes resources for user {user_id}: {str(e)}")
        raise

@shared_task
def delete_user_resources(user_id):
    """删除用户的Kubernetes资源"""
    try:
        k8s = KubernetesManager()
        k8s.delete_user_resources(user_id)
        logger.info(f"Deleted Kubernetes resources for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete Kubernetes resources for user {user_id}: {str(e)}")
        raise