import os
from typing import List
from kubernetes import client, config
import socket
import onceml.orchestration.kubeflow.kfp_config as kfp_config
import onceml.global_config as global_config
import onceml.utils.logger as logger
if os.getenv('{}ENV'.format(global_config.project_name)) == 'INPOD':
    config.load_incluster_config()  #在pod里面
else:  #在集群外
    try:
        config.load_kube_config()
    except:
        logger.logger.error('没有找到kubeconfig文件，有关k8s的api无法使用')
_k8s_client = client.CoreV1Api()
_crd_api = client.CustomObjectsApi()


def get_crd_instance_list(namespace: str, group: str, label_selector: str,
                          version: str, plural: str):
    return _crd_api.list_namespaced_custom_object(
        namespace=namespace,
        group=group,
        version=version,
        plural=plural,
        label_selector=label_selector)


def get_pods_by_label(namespace: str, label_selector: str)->List[client.V1Pod]:
    return _k8s_client.list_namespaced_pod(namespace=namespace,
                                           label_selector=label_selector)['items'] or []


def delete_crd_instance(namespace: str, group: str, name: str, version: str,
                        plural: str):
    _crd_api.delete_namespaced_custom_object(group=group,
                                             version=version,
                                             namespace=namespace,
                                             plural=plural,
                                             name=name)


def get_kfp_host(svc: str, namespace: str):
    return _k8s_client.read_namespaced_service(
        name=svc, namespace=namespace).spec.cluster_ip


def get_pv(pv: str):
    res = None
    try:
        res = _k8s_client.read_persistent_volume(name=pv)
    except:
        return None
    return res


def create_nfs_pv(pvname: str, nfsurl: str, labels: dict):
    try:
        _k8s_client.create_persistent_volume(body=client.V1PersistentVolume(
            api_version='v1',
            kind='PersistentVolume',
            metadata=client.V1ObjectMeta(name=pvname, labels=labels),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=['ReadWriteMany'], )))
    except:
        return False
    return


def get_current_node_host():
    '''获取当前节点在局域网的host
    '''
    # 获取本机电脑名
    #myname = socket.getfqdn(socket.gethostname(  ))
    # 获取本机ip
    machinename = socket.getfqdn(socket.gethostname())
    for value in _k8s_client.read_node_status(
            name=machinename).status.addresses:
        if value.type == 'InternalIP':
            return value.address
    return None


def get_current_node_name():
    '''获取当前节点在局域网的host
    '''
    # 获取本机电脑名
    return socket.getfqdn(socket.gethostname())


def apply_nfs_server(NFS_NAME: str, labels: dict):
    """维护一个工程的nfs server
    """
    NFS_NAME = NFS_NAME.lower()
    try:
        pod = _k8s_client.read_namespaced_pod(name=NFS_NAME,
                                              namespace=kfp_config.NAMESPACE)
        if pod.spec.volumes[0].host_path.path != global_config.PROJECTDIR:
            logger.logger.warning('POD {}已经存在,但挂载目录为{},下面进行更新'.format(
                NFS_NAME, pod.spec.volumes[0].host_path.path))
            _k8s_client.replace_namespaced_pod(
                name=NFS_NAME,
                namespace=kfp_config.NAMESPACE,
                body=client.V1Pod(
                    api_version='v1',
                    kind='Pod',
                    metadata=client.V1ObjectMeta(name=NFS_NAME, labels=labels),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name='nfs-server-container',
                                image=kfp_config.NFS_IMAGE,
                                security_context=client.V1SecurityContext(
                                    privileged=True,
                                    capabilities=client.V1Capabilities(
                                        add=['SYS_ADMIN', 'SETPCAP'])),
                                args=[kfp_config.NFS_DIR],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name="nfs-volume",
                                        mount_path=kfp_config.NFS_DIR)
                                ],
                                ports=[
                                    client.V1ContainerPort(container_port=2049,
                                                           protocol='TCP'),
                                    client.V1ContainerPort(container_port=111,
                                                           protocol='UDP')
                                ])
                        ],
                        volumes=[
                            client.V1Volume(
                                name="nfs-volume",
                                host_path=client.V1HostPathVolumeSource(
                                    path=global_config.PROJECTDIR,
                                    type='Directory'))
                        ],
                        node_selector={
                            "kubernetes.io/hostname":
                            get_current_node_name().lower()
                        })))
        else:
            logger.logger.info('POD {}已经存在,挂载目录为{},无需更新'.format(
                NFS_NAME, pod.spec.volumes[0].host_path.path))
    except:
        logger.logger.warning('POD {}不存在,下面进行新建'.format(NFS_NAME))
        _k8s_client.create_namespaced_pod(
            namespace=kfp_config.NAMESPACE,
            body=client.V1Pod(
                api_version='v1',
                kind='Pod',
                metadata=client.V1ObjectMeta(name=NFS_NAME, labels=labels),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name='nfs-server-container',
                            image=kfp_config.NFS_IMAGE,
                            security_context=client.V1SecurityContext(
                                privileged=True,
                                capabilities=client.V1Capabilities(
                                    add=['SYS_ADMIN', 'SETPCAP'])),
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="nfs-volume",
                                    mount_path=kfp_config.NFS_DIR)
                            ],
                            ports=[
                                client.V1ContainerPort(container_port=2049,
                                                       protocol='TCP'),
                                client.V1ContainerPort(container_port=111,
                                                       protocol='UDP')
                            ],
                            env=[
                                client.V1EnvVar(name='SHARED_DIRECTORY',
                                                value=kfp_config.NFS_DIR)
                            ])
                    ],
                    volumes=[
                        client.V1Volume(
                            name="nfs-volume",
                            host_path=client.V1HostPathVolumeSource(
                                path=global_config.PROJECTDIR,
                                type='Directory'))
                    ],
                    node_selector={
                        "kubernetes.io/hostname":
                        get_current_node_name().lower()
                    })))


def apply_nfs_svc(NFS_SVC_NAME: str, selector: dict):
    """维护一个nfs svc，方便组件挂载
    """
    NFS_SVC_NAME = NFS_SVC_NAME.lower()
    try:
        svc = _k8s_client.read_namespaced_service(
            name=NFS_SVC_NAME, namespace=kfp_config.NAMESPACE)
        logger.logger.info('SVC {}已经存在,无需创建'.format(NFS_SVC_NAME))
    except:
        logger.logger.warning('SVC {}不存在,下面进行新建'.format(NFS_SVC_NAME))
        _k8s_client.create_namespaced_service(
            namespace=kfp_config.NAMESPACE,
            body=client.V1Service(
                api_version='v1',
                kind='Service',
                metadata=client.V1ObjectMeta(name=NFS_SVC_NAME),
                spec=client.V1ServiceSpec(
                    selector=selector,
                    ports=[
                        client.V1ServicePort(name='tcp-2049',
                                             port=2049,
                                             protocol='TCP'),
                        client.V1ServicePort(name="udp-111",
                                             port=111,
                                             protocol="UDP")
                    ])))


def get_nfs_svc_ip(NFS_SVC_NAME: str, namespace: str):
    '''获得某个namespace下svc的ip
    '''
    try:
        svc = _k8s_client.read_namespaced_service(name=NFS_SVC_NAME,
                                                  namespace=namespace)
        return svc.spec.cluster_ip
    except:
        logger.logger.error('SVC {}不存在'.format(NFS_SVC_NAME))
