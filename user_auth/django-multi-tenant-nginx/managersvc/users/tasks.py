from shared.celery import app
# from shared.models import TenantUser
from django.contrib.auth import get_user_model
User = get_user_model()
import time
from kubernetes import client, config
from django.conf import settings
from .k8s import scale_stack, ensure_stack, delete_stack

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def ensure_user_stack_task(self, user_id:int):
    try:
        # user = TenantUser.objects.get(id=user_id)
        user = User.objects.get(id=user_id)
        ensure_stack(user.id, user.namespace or settings.DEFAULT_USER_NS)
    except Exception as e:
        raise self.retry(exc=e)

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def delete_user_stack_task(self, user_id:int, ns:str):
    try:
        delete_stack(user_id, ns)
    except Exception as e:
        raise self.retry(exc=e)

@app.task(bind=True)
def scale_idle_users_task(self, idle_minutes:int=60):
    """
    资源回收：将长时间未访问的用户 Deployment 缩容为 0；有请求时再由 ensure 任务或策略扩容。
    """
    from django.utils import timezone
    from datetime import timedelta
    threshold = timezone.now() - timedelta(minutes=idle_minutes)
    # qs = TenantUser.objects.filter(last_access_at__lt=threshold)
    qs = User.objects.filter(last_access_at__lt=threshold)
    for u in qs:
        try:
            scale_stack(u.id, u.namespace, replicas=0)
        except Exception:
            pass

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def scale_up_user_deployment(self, user_id: int, namespace: str = "default", target_replicas: int = 1):
    """
    将名称为 user-{user_id}-nginx 的 Deployment 副本数调整为 target_replicas，
    并支持 Pod 就绪状态检查及通知等扩展逻辑。
    """
    try:
        # 调用 scale_stack 函数更新副本数
        scale_stack(user_id, namespace, replicas=target_replicas)
        
        # Pod 就绪状态检查
        if settings.K8S_IN_CLUSTER:
            config.load_incluster_config()
        else:
            config.load_kube_config()
        
        a1 = client.AppsV1Api()
        nm = names(user_id, namespace)
        deploy_name = nm["deploy"]
        
        timeout = 60  # 超时时间（秒）
        check_interval = 2  # 检查间隔（秒）
        elapsed_time = 0
        
        while elapsed_time < timeout:
            try:
                deployment = a1.read_namespaced_deployment(name=deploy_name, namespace=namespace)
                available_replicas = deployment.status.available_replicas or 0
                
                if available_replicas >= 1:
                    return {"status": "scaled", "user_id": user_id}
                
                time.sleep(check_interval)
                elapsed_time += check_interval
            except client.exceptions.ApiException as e:
                raise self.retry(exc=e)
        
        # 超时处理
        raise Exception(f"Deployment {deploy_name} in namespace {namespace} did not become ready within {timeout} seconds")
        
    except Exception as e:
        raise self.retry(exc=e)