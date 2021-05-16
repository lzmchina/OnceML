#包含镜像的一些信息

IMAGE='liziming/onceml:latest'
COMMAND='python3 -m onceml.orchestration.kubeflow.container_entrypoint'
WORKINGDIR='/project'#工程被挂载的目录，会在这里面执行命令
SERVERPORT=8080
EXPERIMENT='.onceml'
SVCNAME='ml-pipeline-ui'
NAMESPACE='kubeflow'