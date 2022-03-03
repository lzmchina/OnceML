import onceml.global_config as global_config

COMMAND = ['python3', '-m', '{}.container_entrypoint'.format(__package__)]
IMAGE = 'liziming/{}:latest'.format(global_config.project_name)
WORKINGDIR = '/project'  # 容器里代码工程被挂载的目录，会在这里面执行命令
SERVERPORT = global_config.SERVERPORT


def generate_workflow_name(prefix, pipeline_id):
    """生成workflow的唯一限定名
    """
    return "{}.{}".format(prefix, pipeline_id)


def generate_pipeline_id(task_name, model_name):
    """生成pipeline ID
    """
    return "{}.{}".format(task_name, model_name)
