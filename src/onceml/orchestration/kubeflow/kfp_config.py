
import onceml.global_config as global_config
import os
#包含镜像的一些信息
IMAGE='liziming/{}:latest'.format(global_config.project_name)
COMMAND='python3 -m {}.orchestration.kubeflow.container_entrypoint'.format(global_config.project_name)
WORKINGDIR='/project'#工程被挂载的目录，会在这里面执行命令
SERVERPORT=8080
EXPERIMENT='.{}'.format(global_config.project_name)
SVCNAME='ml-pipeline-ui'
NAMESPACE='kubeflow'
kFPOUTPUT=os.path.join(os.getcwd(),'kfpoutput')