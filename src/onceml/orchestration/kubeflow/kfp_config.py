import onceml.global_config as global_config
import os
# 包含镜像的一些信息
IMAGE = 'liziming/{}:0.0.1'.format(global_config.project_name)
COMMAND = [
    'python3', '-m', '{}.orchestration.kubeflow.container_entrypoint'.format(
        global_config.project_name)
]
WORKINGDIR = '/project'  # 容器里代码工程被挂载的目录，会在这里面执行命令

SERVERPORT = 8080

SVCNAME = 'ml-pipeline-ui'
NAMESPACE = 'kubeflow'
#workflow crd的信息
wf_group = 'argoproj.io'
wf_version = 'v1alpha1'
wf_plural = 'workflows'

# 如果不指定kfp的输出目录，则采用默认路径
KFPOUTPUT = os.path.join(global_config.PROJECTDIR, global_config.OUTPUTSDIR)
# pv pvc
PVNAME_PRE = 'pv-' + global_config.project_name
COMPONENT_POD_LABEL = '{}.component.id'.format(
    global_config.project_name).lower()
PV_LABEL = '{}.pv'.format(global_config.project_name)
EXPERIMENT = '.{}-{}'.format(global_config.project_name,
                             global_config.PROJECTDIRNAME)
RUNS_PAGE_SIZE = 30
# 供需要向后续节点发送消息的Cycle类型
COMPONENT_SENDER_POD_LABEL = '{tool}.{project}.{{task}}.{{model}}.{{component}}'.format(
    tool=global_config.project_name,
    project=global_config.PROJECTDIRNAME).lower()
# NFS容器相关
#NFS_IMAGE = 'gists/nfs-server'#cpuguy83/nfs-server itsthenetwork/nfs-server-alpine
NFS_IMAGE = 'itsthenetwork/nfs-server-alpine'
NFS_NAME = 'nfs-server' + '-' + global_config.PROJECTDIRNAME
NFS_DIR = '/nfs-share'
NFS_POD_LABEL_KEY = '.'.join([global_config.project_name, 'nfs'])
NFS_SVC_NAME = 'nfs-server' + '-' + global_config.PROJECTDIRNAME
NFS_SVC_DNS = "{}.kubeflow.svc.cluster.local".format(NFS_SVC_NAME)
NFS_POD_TEMPLATE = '''{{
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {{
        "name": {NFS_NAME},
        "labels":{labels}
    }},
    "spec": {{
        "containers":[{{
            "name":"nfs-server-container",
            "image":{NFS_IMAGE},
            "securityContext":{{
                "privileged": true
            }},
            "args":[
                {NFS_DIR}
            ]
        }}],
        "volumes":[
            {{
                "name":"nfs-volume",
                "hostPath":{{
                    "path":{PROJECT_DIR},
                    "type":"Directory"
                }}
            }}
        ],
        "nodeSelector":{nodeSelector}
       
    }}
}}'''
NFS_SVC_TEMPLATE = """
{{
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {{
        "name": {NFS_SVC_NAME}
    }},
    "spec": {{
        "ports":[
            {{
                "name":"tcp-2049",
                "port":2049,
                "protocol":"TCP"
            }},
            {{
                "name":"udp-111",
                "port":111,
                "protocol":"UDP"
            }}
        ],
        "selector":{nodeSelector}
    }}
}}
"""
