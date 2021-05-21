
import onceml.global_config as global_config
import os
import onceml.utils.k8s_ops as k8s_ops
# 包含镜像的一些信息
IMAGE = 'liziming/{}:latest'.format(global_config.project_name)
COMMAND = 'python3 -m {}.orchestration.kubeflow.container_entrypoint'.format(
    global_config.project_name)
WORKINGDIR = '/project'  # 容器里代码工程被挂载的目录，会在这里面执行命令
OUTPUTSDIR = '/kfpoutputs'  # 容器里被挂载的kfp输出目录，每个组件的输出会保存在这

SERVERPORT = 8080

SVCNAME = 'ml-pipeline-ui'
NAMESPACE = 'kubeflow'
# 如果不指定kfp的输出目录，则采用默认路径
KFPOUTPUT = os.path.join(global_config.PROJECTDIR, 'kfpoutputs')
PVNAME_PRE = 'pv-'+global_config.project_name
COMPONENT_POD_LABEL = '{}.component.id'.format(global_config.project_name)
PV_LABEL = '{}.pv'.format(global_config.project_name)
EXPERIMENT = '.{}-{}'.format(global_config.project_name, global_config.PROJECTDIRNAME)
RUNS_PAGE_SIZE = 30

# NFS容器相关
NFS_IMAGE = 'cpuguy83/nfs-server'
NFS_NAME = 'nfs-server-pod'
NFS_DIR = '/exports'
NFS_POD_LABEL_KEY='.'.join([global_config.project_name,'nfs'])
NFS_POD_TEMPLATE = """
{"apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": {NFS_NAME},
        "labels":{labels},
    },
    "spec": {
        "containers":[{
            "name":"nfs-server-container",
            "image":{NFS_IMAGE},
            "securityContext":{
                "privileged": true
            },
            "args":[
                {NFS_DIR}
            ]
        }],
        "volumes":[
            {
                "name":"nfs-volume",
                "hostPath":{
                    "path":{PROJECT_DIR},
                    "type":"Directory"
                }
            }
        ],
        "nodeSelector":{nodeSelector}
       
    }
}
""".format(#先将nfs的pod运行在当前代码的节点上，同时将代码目录挂载
    nodeSelector={"kubernetes.io/hostname":k8s_ops.get_current_node_name},
    NFS_IMAGE=NFS_IMAGE,
    NFS_DIR=NFS_DIR,
    PROJECT_DIR=global_config.PROJECTDIR
    )
NFS_SVC_TEMPLATE="""
{
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
        "name": {NFS_SVC_NAME}
    },
    "spec": {
        "ports":[
            {
                "name":"tcp-2049",
                "port":2049,
                "protocol":"TCP"
            },
            {
                "name":"udp-111",
                "port":111,
                "protocol":"UDP"
            }
        ],
        "selector":{nodeSelector}
    }
}
"""
