from kubernetes import client, config
config.load_kube_config()
_k8s_client=client.CoreV1Api()
def get_kfp_host(svc:str,namespace:str):
    return _k8s_client.read_namespaced_service(name=svc,namespace=namespace).spec.cluster_ip

