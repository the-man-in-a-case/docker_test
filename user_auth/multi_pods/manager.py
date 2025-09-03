"""
manager.py

- 初始状态下作为稳定的单容器Pod运行，提供HTTP接口
- 接收到特定POST请求后，使用in-cluster kubeconfig修改自身所在的Deployment
- 将podTemplate替换为多容器模板，添加时间戳触发滚动更新
- 包含错误处理和重试机制，确保配置更新成功
"""
import os
import time
import logging
import json
import http.server
import socketserver
from urllib.parse import parse_qs
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pod-configurator')

# 环境变量
NAMESPACE = os.environ.get('POD_NAMESPACE', 'default')
DEPLOYMENT_NAME = os.environ.get('DEPLOYMENT_NAME', 'manager-deployment')
# 添加重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒
# HTTP服务器配置
HTTP_PORT = int(os.environ.get('HTTP_PORT', '8080'))
TRIGGER_ENDPOINT = '/trigger-update'
AUTH_TOKEN = os.environ.get('AUTH_TOKEN', 'default-token')  # 简单的认证机制

# 多容器模板配置
MULTI_CONTAINERS_TEMPLATE = {
    "spec": {
        "template": {
            "metadata": {
                "annotations": {
                    "updated-by": "manager-script"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "testserver",
                        "image": "nginx:alpine",  # 使用公共镜像替代自定义镜像
                        "ports": [{"containerPort": 80}],
                        "env": [{"name": "ROLE", "value": "server"}],
                        "resources": {
                            "requests": {
                                "cpu": "10m",
                                "memory": "32Mi"
                            },
                            "limits": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        }
                    },
                    {
                        "name": "testclient",
                        "image": "busybox:latest",  # 使用公共镜像替代自定义镜像
                        "env": [{"name": "ROLE", "value": "client"}],
                        "command": ["/bin/sh", "-c", "sleep infinity"],  # 保持容器运行
                        "resources": {
                            "requests": {
                                "cpu": "10m",
                                "memory": "32Mi"
                            },
                            "limits": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        }
                    }
                ],
                "dnsPolicy": "ClusterFirst",
                "restartPolicy": "Always"
            }
        }
    }
}


class ConfiguratorHandler(http.server.BaseHTTPRequestHandler):
    """处理HTTP请求的处理器"""
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == TRIGGER_ENDPOINT:
            # 验证请求中的认证令牌
            auth_header = self.headers.get('Authorization')
            if not auth_header or not self._validate_auth_token(auth_header):
                self._send_response(401, {"status": "error", "message": "Unauthorized"})
                return
            
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            logger.info(f"接收到配置更新触发请求: {post_data}")
            
            try:
                # 执行配置更新
                self._perform_config_update()
                self._send_response(200, {"status": "success", "message": "配置更新已触发"})
            except Exception as e:
                logger.error(f"配置更新失败: {str(e)}")
                self._send_response(500, {"status": "error", "message": str(e)})
        else:
            self._send_response(404, {"status": "error", "message": "Not found"})
    
    def do_GET(self):
        """处理GET请求，提供简单的状态信息"""
        if self.path == '/':
            status_info = {
                "status": "running",
                "deployment": DEPLOYMENT_NAME,
                "namespace": NAMESPACE,
                "trigger_endpoint": TRIGGER_ENDPOINT,
                "instructions": "发送POST请求到/trigger-update以触发配置更新"
            }
            self._send_response(200, status_info)
        else:
            self._send_response(404, {"status": "error", "message": "Not found"})
    
    def _validate_auth_token(self, auth_header: str) -> bool:
        """验证认证令牌"""
        # 简单的Bearer令牌验证
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            return token == AUTH_TOKEN
        return False
    
    def _send_response(self, status_code: int, data: Dict[str, Any]):
        """发送HTTP响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _perform_config_update(self):
        """执行配置更新操作"""
        # 初始化Kubernetes客户端
        apps_v1 = setup_kubernetes_client()
        
        # 读取当前Deployment
        get_current_deployment(apps_v1)
        
        # 创建多容器配置补丁
        patch = create_patch()
        
        # 应用补丁
        apply_deployment_patch(apps_v1, patch)
        
        # 验证补丁应用
        verify_patch_application(apps_v1)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """支持多线程的HTTP服务器"""
    daemon_threads = True


def setup_kubernetes_client() -> client.AppsV1Api:
    """设置Kubernetes客户端"""
    try:
        config.load_incluster_config()
        logger.info("成功加载in-cluster配置")
        return client.AppsV1Api()
    except Exception as e:
        logger.error(f"加载Kubernetes配置失败: {str(e)}")
        raise


def get_current_deployment(apps_v1: client.AppsV1Api) -> Dict[str, Any]:
    """获取当前Deployment配置"""
    for attempt in range(MAX_RETRIES):
        try:
            deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)
            logger.info(f"成功读取Deployment {DEPLOYMENT_NAME}，当前副本数: {deployment.spec.replicas}")
            return deployment
        except ApiException as e:
            logger.error(f"读取Deployment失败 (尝试 {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


def create_patch() -> Dict[str, Any]:
    """创建Deployment补丁以更新为多容器配置"""
    patch = {
        "spec": {
            "template": MULTI_CONTAINERS_TEMPLATE['spec']['template']
        }
    }
    
    # 添加时间戳确保滚动更新被触发
    ts = str(int(time.time()))
    patch['spec']['template']['metadata'].setdefault('annotations', {})
    patch['spec']['template']['metadata']['annotations']['updated-at'] = ts
    patch['spec']['template']['metadata']['annotations']['original-containers'] = 'single'
    patch['spec']['template']['metadata']['annotations']['triggered-by'] = 'http-request'
    
    logger.info(f"创建补丁配置，时间戳: {ts}")
    return patch


def apply_deployment_patch(apps_v1: client.AppsV1Api, patch: Dict[str, Any]) -> None:
    """应用Deployment补丁"""
    for attempt in range(MAX_RETRIES):
        try:
            apps_v1.patch_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=patch)
            logger.info(f"成功应用Deployment补丁")
            return
        except ApiException as e:
            logger.error(f"应用Deployment补丁失败 (尝试 {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


def verify_patch_application(apps_v1: client.AppsV1Api) -> bool:
    """验证补丁是否成功应用"""
    try:
        deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, NAMESPACE)
        annotations = deployment.spec.template.metadata.annotations or {}
        if 'updated-at' in annotations and annotations.get('original-containers') == 'single':
            logger.info("补丁应用验证成功")
            return True
        else:
            logger.warning("补丁应用验证失败，注解不匹配")
            return False
    except Exception as e:
        logger.error(f"验证补丁应用失败: {str(e)}")
        return False


def start_http_server() -> None:
    """启动HTTP服务器"""
    server_address = ('', HTTP_PORT)
    httpd = ThreadedHTTPServer(server_address, ConfiguratorHandler)
    logger.info(f"HTTP服务器启动在端口 {HTTP_PORT}")
    logger.info(f"使用POST请求到 {TRIGGER_ENDPOINT} 触发配置更新")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("接收到终止信号，关闭HTTP服务器")
    finally:
        httpd.server_close()


def main():
    """主函数"""
    logger.info(f"Pod配置管理器启动，目标Deployment: {DEPLOYMENT_NAME}，命名空间: {NAMESPACE}")
    
    # 启动HTTP服务器，等待触发请求
    start_http_server()
    
    logger.info("Pod配置管理器退出")


if __name__ == '__main__':
    main()