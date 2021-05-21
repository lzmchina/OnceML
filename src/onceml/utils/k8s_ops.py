from os import name
from kubernetes import client, config
import socket

config.load_kube_config()
_k8s_client = client.CoreV1Api()


def get_kfp_host(svc: str, namespace: str):
    return _k8s_client.read_namespaced_service(name=svc, namespace=namespace).spec.cluster_ip


def get_pv(pv: str):
    res=None
    try:
        res = _k8s_client.read_persistent_volume(name=pv)
    except:
        return None
    return res


def create_nfs_pv(pvname: str, nfsurl: str,labels:dict):
    try:
        _k8s_client.create_persistent_volume(body=
        client.V1PersistentVolume(

            api_version='v1',
            kind='PersistentVolume',
            metadata=client.V1ObjectMeta(
                name=pvname,
                labels=labels
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=['ReadWriteMany'],
                
            )
        )
    )
    except:
        return False
    return 


def get_current_node_host():
    '''获取当前节点在局域网的host
    '''
    # 获取本机电脑名
    #myname = socket.getfqdn(socket.gethostname(  ))
    # 获取本机ip
    machinename=socket.getfqdn(socket.gethostname())
    for value in _k8s_client.read_node_status(name=machinename).status.addresses:
        if value.type=='InternalIP':
            return value.address
    return None
def get_current_node_name():
    '''获取当前节点在局域网的host
    '''
    # 获取本机电脑名
    return socket.getfqdn(socket.gethostname())
