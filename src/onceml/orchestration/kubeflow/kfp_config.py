
import onceml.global_config as global_config
import os
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
kFPOUTPUT = os.path.join(os.getcwd(), 'kfpoutput')
PVNAME_PRE = 'pv-'+global_config.project_name
COMPONENT_POD_LABEL = 'onceml.component.id'
PV_LABEL = 'onceml.pv'
PROJECTDIR = os.getcwd()
# 当前运行项目的根目录名
PROJECTDIRNAME = os.path.split(PROJECTDIR)[1]
# 当前运行项目的父路径
PROJECTPARENtDIR = os.path.split(PROJECTDIR)[0]

EXPERIMENT = '.{}-{}'.format(global_config.project_name, PROJECTDIRNAME)

RUNS_PAGE_SIZE = 30
