import os
import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import uuid

class KubernetesManager:
    def __init__(self):
        # 在集群内使用服务账户，集群外使用kubeconfig
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            config.load_incluster_config()
        else:
            config.load_kube_config()
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.networking_v1 = client.NetworkingV1Api()

    def create_namespace(self, namespace_name):
        """创建用户专属命名空间"""
        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={'app.kubernetes.io/managed-by': 'user-management-system'}
            )
        )
        try:
            return self.v1.create_namespace(body=namespace)
        except ApiException as e:
            if e.status == 409:  # 已存在
                return self.v1.read_namespace(namespace_name)
            raise

    def create_user_nginx_deployment(self, user_id, username):
        """为用户创建Nginx部署"""
        namespace = f"user-{user_id}"
        deployment_name = f"nginx-{username}"
        
        # 创建命名空间
        self.create_namespace(namespace)
        
        # 创建Nginx配置
        nginx_config = f"""
        server {{
            listen 80;
            server_name _;
            
            location / {{
                root /usr/share/nginx/html;
                index index.html;
                try_files $uri $uri/ =404;
            }}
            
            location /health {{
                access_log off;
                return 200 "healthy\\n";
                add_header Content-Type text/plain;
            }}
            
            # 用户专属配置
            location /user-info {{
                return 200 '{{"user_id": "{user_id}", "username": "{username}"}}';
                add_header Content-Type application/json;
            }}
        }}
        """
        
        # 创建ConfigMap
        config_map = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=f"nginx-config-{username}",
                namespace=namespace
            ),
            data={'default.conf': nginx_config}
        )
        
        try:
            self.v1.create_namespaced_config_map(namespace=namespace, body=config_map)
        except ApiException as e:
            if e.status != 409:
                raise

        # 创建Deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                namespace=namespace,
                labels={'app': 'nginx', 'user-id': user_id}
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={'app': 'nginx', 'user-id': user_id}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={'app': 'nginx', 'user-id': user_id}
                    ),
                    spec=client.V1PodSpec(
                        containers=[client.V1Container(
                            name='nginx',
                            image='nginx:alpine',
                            ports=[client.V1ContainerPort(container_port=80)],
                            volume_mounts=[client.V1VolumeMount(
                                name='nginx-config',
                                mount_path='/etc/nginx/conf.d'
                            )],
                            readiness_probe=client.V1Probe(
                                http_get=client.V1HTTPGetAction(
                                    path='/health',
                                    port=80
                                ),
                                initial_delay_seconds=5,
                                period_seconds=10
                            )
                        )],
                        volumes=[client.V1Volume(
                            name='nginx-config',
                            config_map=client.V1ConfigMapVolumeSource(
                                name=f'nginx-config-{username}'
                            )
                        )]
                    )
                )
            )
        )

        try:
            return self.apps_v1.create_namespaced_deployment(
                namespace=namespace,
                body=deployment
            )
        except ApiException as e:
            if e.status != 409:
                raise
            return self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )

    def create_user_service(self, user_id, username):
        """为用户Nginx创建Service"""
        namespace = f"user-{user_id}"
        service_name = f"nginx-service-{username}"
        
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=namespace,
                labels={'app': 'nginx', 'user-id': user_id}
            ),
            spec=client.V1ServiceSpec(
                selector={'app': 'nginx', 'user-id': user_id},
                ports=[client.V1ServicePort(
                    port=80,
                    target_port=80,
                    protocol='TCP'
                )],
                type='ClusterIP'
            )
        )
        
        return self.v1.create_namespaced_service(
            namespace=namespace, 
            body=service
        )

    def create_user_ingress(self, user_id, username):
        """为用户创建Ingress路由"""
        namespace = f"user-{user_id}"
        ingress_name = f"user-ingress-{username}"
        
        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(
                name=ingress_name,
                namespace=namespace,
                annotations={
                    'nginx.ingress.kubernetes.io/rewrite-target': '/',
                    'nginx.ingress.kubernetes.io/ssl-redirect': 'false',
                    'nginx.ingress.kubernetes.io/auth-url': 'http://auth-service.user-platform.svc.cluster.local:8000/api/auth/verify/',
                    'nginx.ingress.kubernetes.io/auth-signin': 'http://auth-service.user-platform.svc.cluster.local:8000/api/auth/login/',
                }
            ),
            spec=client.V1IngressSpec(
                ingress_class_name='nginx',
                rules=[client.V1IngressRule(
                    host=f"{username}.localhost",
                    http=client.V1HTTPIngressRuleValue(
                        paths=[client.V1HTTPIngressPath(
                            path='/',
                            path_type='Prefix',
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    name=f"nginx-service-{username}",
                                    port=client.V1ServiceBackendPort(number=80)
                                )
                            )
                        )]
                    )
                )]
            )
        )
        
        return self.networking_v1.create_namespaced_ingress(
            namespace=namespace, 
            body=ingress
        )

    def delete_user_resources(self, user_id):
        """删除用户的所有Kubernetes资源"""
        namespace = f"user-{user_id}"
        
        try:
            # 删除命名空间（会删除所有资源）
            self.v1.delete_namespace(name=namespace)
            return True
        except ApiException as e:
            if e.status == 404:
                return True  # 命名空间不存在，视为已删除
            raise

    def get_user_resource_status(self, user_id):
        """获取用户Kubernetes资源状态"""
        namespace = f"user-{user_id}"
        
        try:
            # 检查命名空间
            namespace_obj = self.v1.read_namespace(namespace)
            
            # 检查部署
            deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)
            
            # 检查服务
            services = self.v1.list_namespaced_service(namespace=namespace)
            
            # 检查Ingress
            ingresses = self.networking_v1.list_namespaced_ingress(namespace=namespace)
            
            return {
                'namespace': namespace_obj.metadata.name if namespace_obj else None,
                'deployments': len(deployments.items),
                'services': len(services.items),
                'ingresses': len(ingresses.items),
                'status': 'active' if namespace_obj else 'not_found'
            }
        except ApiException as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def update_user_nginx_config(self, user_id, username, new_config):
        """更新用户的Nginx配置"""
        namespace = f"user-{user_id}"
        config_map_name = f"nginx-config-{username}"

        # 更新ConfigMap
        config_map = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=config_map_name,
                namespace=namespace
            ),
            data={'default.conf': new_config}
        )

        try:
            return self.v1.patch_namespaced_config_map(
                name=config_map_name,
                namespace=namespace,
                body=config_map
            )
        except ApiException as e:
            raise

    def get_user_nginx_logs(self, user_id, username, tail_lines=100):
        """获取用户Nginx Pod的日志"""
        namespace = f"user-{user_id}"
        pod_name = f"nginx-{username}-"

        # 查找Pod
        pods = self.v1.list_namespaced_pod(namespace=namespace)
        target_pod = None
        for pod in pods.items:
            if pod.metadata.name.startswith(pod_name):
                target_pod = pod.metadata.name
                break

        if not target_pod:
            raise Exception(f"Pod for user {username} not found")

        # 获取日志
        try:
            log = self.v1.read_namespaced_pod_log(
                name=target_pod,
                namespace=namespace,
                container='nginx',
                tail_lines=tail_lines
            )
            return log
        except ApiException as e:
            raise

    def scale_user_deployment(self, user_id, username, replicas=1):
        """调整用户Nginx部署的副本数"""
        namespace = f"user-{user_id}"
        deployment_name = f"nginx-{username}"

        # 缩放部署
        body = {"spec": {"replicas": replicas}}

        try:
            return self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=body
            )
        except ApiException as e:
            raise