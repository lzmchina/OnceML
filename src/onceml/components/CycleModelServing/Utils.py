from logging import Logger, log
import time
from onceml.utils import pipeline_utils
from onceml.utils.http import syncPost
from onceml.types.ts_config import TsConfig
from onceml.utils.logger import logger

def registerModelJob(url: str, handler: str, initial_workers=1,maxtry=5) -> bool:
    """向ts serving注册一个model serving
    1. url:.mar压缩包的路径(相对于model store文件夹)
    2. handler:server handler的py文件路径
    3. initial_workers:初始化的worker
    return:

    """

    logger.info(url+" "+handler)
    while maxtry > 0:
        try:
            reponse = syncPost("http://127.0.0.1:{}/models".format(8081), data={
                "url": url,
                #"handler": handler,
                "initial_workers": initial_workers
            })
            logger.info(reponse.text)
            if reponse.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            logger.error(e)
        time.sleep(2)
        maxtry -= 1
    return False


def get_handler_path():
    """获得custom handler的py文件路径
    """
    import onceml.thirdParty.PyTorchServing.PyTorchServingHandler as PyTorchServingHandler
    return PyTorchServingHandler.__file__


def get_handler_module():
    """获得custom handler的py文件的module路径
    """
    import onceml.thirdParty.PyTorchServing.PyTorchServingHandler as PyTorchServingHandler
    return PyTorchServingHandler.__name__


def generate_onceml_config_json(working_dir: str, module: str, cls_name: str, project_name: str, task: str, model: str):
    """生成handler runtime需要的onceml_config.yaml文件
    1. working_dir:用户项目的工作目录
    2. module:用户的model serving class的module 
    3. cls_name:用户的model serving class的name
    """
    onceml_config = TsConfig()
    onceml_config.serving_class = (module, cls_name)
    onceml_config.working_dir = working_dir
    onceml_config.task_name = task
    onceml_config.model_name = model
    onceml_config.project_name = project_name
    return onceml_config


def get_svc_name(project_name, task_name, model_name):
    """获得project_name下的task_name下的model_name对应的serving svc
    必须与workflow operator的svc名字生成方式一致
    """
    component=pipeline_utils.get_pipeline_model_serving_component_id(task_name, model_name)
    if component is None:
        return ""
    return component.replace(".","-")
