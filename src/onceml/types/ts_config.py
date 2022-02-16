from types import resolve_bases
from typing import Tuple
from onceml.utils.json_utils import Jsonable


class TsConfig(Jsonable):
    """用于onceml框架生成torch serving框架需要的模型配置信息

    将该信息保存成json文件，打包进.mar压缩包里面，然后torch serving model运行时再恢复
    """

    def __init__(self) -> None:
        self._working_dir = None
        self._model_serving_class_module = ""
        self._model_serving_class_name = ""
        self._task_name = ""
        self._model_name = ""
        self._project_name = ""

    @property
    def task_name(self):
        return self._task_name

    @task_name.setter
    def task_name(self, task: str):
        """设置task name
        """
        self._task_name = task

    @property
    def model_name(self):
        return self._model_name

    @model_name.setter
    def model_name(self, model: str):
        self._model_name = model

    @property
    def working_dir(self):
        """获取oncmel项目的工作目录，因为db数据库在这个目录，torch serving handler的runtime的工作目录是在
        /tmp/models/xxxxxxx/下，因此需要将运行环境进行切换（设置db的path、增加sys.path的搜索路径）
        """
        return self._working_dir

    @working_dir.setter
    def working_dir(self, path: str):
        self._working_dir = path

    @property
    def serving_class(self):
        """获得用户的serving class
        """
        return self._model_serving_class_module, self._model_serving_class_name

    @serving_class.setter
    def serving_class(self, module_cls_name: Tuple[str, str]):
        self._model_serving_class_module = module_cls_name[0]
        self._model_serving_class_name = module_cls_name[1]

    @property
    def project_name(self):
        """获得project name
        """
        return self._project_name

    @project_name.setter
    def project_name(self, project_name):
        self._project_name = project_name
