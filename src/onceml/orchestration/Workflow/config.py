import onceml.global_config as global_config

COMMAND = ['python3', '-m', '{}.container_entrypoint'.format(__package__)]
IMAGE = 'liziming/{}:latest'.format(global_config.project_name)
WORKINGDIR = '/project'  # 容器里代码工程被挂载的目录，会在这里面执行命令
SERVERPORT=global_config.SERVERPORT