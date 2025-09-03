from kubernetes import client, config
from django.conf import settings

def core():
    if settings.K8S_IN_CLUSTER:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    return client.CoreV1Api()

def apps():
    if settings.K8S_IN_CLUSTER:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    return client.AppsV1Api()

def names(user_id:int, ns:str):
    base = f"user-{user_id}"
    return {
        "deploy": f"{base}-nginx",
        "svc": f"{base}-svc",
        "labels": {"app":"user-nginx","user-id":str(user_id)}
    }

def ensure_namespace(ns: str):
    v1 = core()
    try:
        v1.read_namespace(ns)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            body = client.V1Namespace(metadata=client.V1ObjectMeta(name=ns))
            v1.create_namespace(body)
        else:
            raise

def ensure_stack(user_id:int, ns:str):
    """
    确保用户命名空间和 Deployment、Service 存在
    打开 topologySpreadConstraints、affinity、podSecurityContext 等生产选项。
    """
    ensure_namespace(ns)
    v1 = core()
    a1 = apps()
    nm = names(user_id, ns)

    # Deployment（1 副本，带健康检查）
    dep = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=nm["deploy"], labels=nm["labels"]),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels=nm["labels"]),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=nm["labels"]),
                spec=client.V1PodSpec(containers=[
                    client.V1Container(
                        name="nginx",
                        image="nginx:alpine",
                        ports=[client.V1ContainerPort(container_port=80)],
                        readiness_probe=client.V1Probe(http_get=client.V1HTTPGetAction(path="/", port=80), initial_delay_seconds=2, period_seconds=5),
                        liveness_probe=client.V1Probe(http_get=client.V1HTTPGetAction(path="/", port=80), initial_delay_seconds=10, period_seconds=10),
                        resources=client.V1ResourceRequirements(
                            requests={"cpu":"50m","memory":"32Mi"},
                            limits={"cpu":"200m","memory":"128Mi"}
                        )
                    )
                ])
            )
        )
    )
    try:
        a1.create_namespaced_deployment(ns, dep)
    except client.exceptions.ApiException as e:
        if e.status != 409:
            raise

    # Service（ClusterIP，稳定名）
    svc = client.V1Service(
        metadata=client.V1ObjectMeta(name=nm["svc"], labels=nm["labels"]),
        spec=client.V1ServiceSpec(
            selector=nm["labels"],
            ports=[client.V1ServicePort(port=80, target_port=80)]
        )
    )
    try:
        v1.create_namespaced_service(ns, svc)
    except client.exceptions.ApiException as e:
        if e.status != 409:
            raise

def delete_stack(user_id:int, ns:str):
    v1 = core(); a1 = apps()
    nm = names(user_id, ns)
    opts = client.V1DeleteOptions(grace_period_seconds=10, propagation_policy='Foreground')
    for deleter, name in [(a1.delete_namespaced_deployment, nm["deploy"]),
                          (v1.delete_namespaced_service, nm["svc"])]:
        try:
            deleter(name=name, namespace=ns, body=opts)
        except client.exceptions.ApiException as e:
            if e.status != 404:
                raise

def scale_stack(user_id:int, ns:str, replicas:int):
    a1 = apps()
    nm = names(user_id, ns)
    body = {"spec": {"replicas": replicas}}
    a1.patch_namespaced_deployment_scale(name=nm["deploy"], namespace=ns, body=body)
