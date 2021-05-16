from kubernetes import client, config
config.load_kube_config()
_k8s_client=client.CoreV1Api()
def get_kfp_host(svc:str,namespace:str):
    print(_k8s_client.list_namespaced_service(namespace=namespace))

