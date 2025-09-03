import os
import yaml
from kubernetes import client, config
from kubernetes.client import ApiException

NAMESPACE = os.getenv("K8S_NAMESPACE", "user-health")

def get_clients():
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()
    return client.AppsV1Api(), client.CoreV1Api()

# Nginx + Sidecar（带 /status，sidecar 9000 对内健康）
DEPLOYMENT_TEMPLATE = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-user-{user}
  namespace: {namespace}
  labels:
    app: nginx-user
    user: "{user}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx-user
      user: "{user}"
  template:
    metadata:
      labels:
        app: nginx-user
        user: "{user}"
    spec:
      serviceAccountName: nginx-user-sa
      volumes:
      - name: nginx-logs
        emptyDir: {{}}
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-logs
          mountPath: /var/log/nginx
        # readinessProbe:
        #   httpGet: {{ path: /status, port: 80 }}
        #   initialDelaySeconds: 5
        #   periodSeconds: 10
        # livenessProbe:
        #   httpGet: {{ path: /status, port: 80 }}
        #   initialDelaySeconds: 30
        #   periodSeconds: 20
      - name: sidecar-detector
        image: {sidecar_image}
        imagePullPolicy: IfNotPresent
        env:
        - name: HEALTH_SERVICE_URL
          value: "{health_service_url}"
        - name: USER_ID
          value: "{user}"
        - name: POD_NAME
          valueFrom: {{ fieldRef: {{ fieldPath: metadata.name }} }}
        - name: NGINX_ERROR_LOG
          value: "/var/log/nginx/error.log"
        ports:
        - containerPort: 9000
          name: detector
        volumeMounts:
        - name: nginx-logs
          mountPath: /var/log/nginx
"""

def _render_manifest(user: str, sidecar_image: str, health_service_url: str, namespace: str):
    return yaml.safe_load(DEPLOYMENT_TEMPLATE.format(
        user=user, sidecar_image=sidecar_image, health_service_url=health_service_url, namespace=namespace
    ))

def create_user_deployment(user: str, sidecar_image: str, health_service_url: str, namespace=NAMESPACE):
    apps_v1, _ = get_clients()
    name = f"nginx-user-{user}"
    body = _render_manifest(user, sidecar_image, health_service_url, namespace)
    try:
        apps_v1.create_namespaced_deployment(namespace=namespace, body=body)
        print(f"[Django] Created Deployment {name}")
    except ApiException as e:
        if e.status == 409:
            apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=body)
            print(f"[Django] Patched Deployment {name}")
        else:
            raise

def delete_user_deployment(user: str, namespace=NAMESPACE):
    apps_v1, _ = get_clients()
    name = f"nginx-user-{user}"
    try:
        apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)
        print(f"[Django] Deleted Deployment {name}")
    except ApiException as e:
        if e.status != 404:
            raise
