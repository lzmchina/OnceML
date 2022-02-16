import abc
import importlib
import json
import os
import sys
from typing import Any, ClassVar, Dict, List, Type
import onceml.utils.db as db
from onceml.types.exception import CustomError
from onceml.utils.http import asyncMsg
from onceml.utils.json_utils import objectLoads
from onceml.types.ts_config import TsConfig
from onceml.templates.ModelServing import ModelServing
from onceml.utils.logger import logger
from onceml.components.CycleModelTrain.ModelDag import ModelNode, getModelNode
from onceml.components.CycleModelServing.Utils import get_svc_name
from onceml.thirdParty.PyTorchServing.config import inference_port


class ModelHandler():
    """A custom model handler implementation.
    这个文件会用于torchserving框架使用，作为custom model handler。用户写完ModelServing的子类后，这里会实例化。
    """

    def __init__(self):
        self.model = None
        self.model_dir = None
        self.onceml_config: TsConfig = None
        self.cls = None
        self.cls_instance = None  # type:ModelServing
        self.task_name = ""
        self.model_name = ""
        self.project_name = ""

    def initialize(self, context):
        """
        Invoke by torchserve for loading a model
        :param context: context contains model server system properties
        :return:
        """
        properties = context.system_properties  # type:Dict
        # 获取pytorch serving的模型目录，为/tmp/models/xxxxxxx/
        self.model_dir = properties.get("model_dir")
        # 加载onceml传来的配置信息
        with open(os.path.join(self.model_dir, "onceml_config.json")) as f:
            self.onceml_config: TsConfig = objectLoads(f.read())
        self.task_name = self.onceml_config.task_name
        self.model_name = self.onceml_config.model_name
        self.project_name = self.onceml_config.project_name
        # 将python的module搜索路径进行拓展,让handler的runtime能够搜索到用户工程
        sys.path = [self.onceml_config.working_dir]+sys.path
        # 设置onceml的db的path
        db.change_path_context(self.onceml_config.working_dir)
        # 将用户的ModelServing class加载进来
        module_name, class_name = self.onceml_config.serving_class
        try:
            self.cls = getattr(importlib.import_module(module_name), class_name)
        except Exception as e:
            with open(os.path.join(self.onceml_config.working_dir, "handler.log"), "a") as f:
                f.write(e)
        # 将这个路径作为checkpoints路径传入
        self.cls_instance: ModelServing = self.cls(self.model_dir)

    def preprocess(self, data):
        """主要获得上游模型的输出，如果有的话

        """
        model_node = getModelNode(self.task_name, self.model_name)
        up_models = []
        if model_node is not None:
            up_models = [node.model_name for node in model_node.up_models]
        up_model_serving_svc = {}
        for model_name in up_models:
            up_model_serving_svc[model_name] = get_svc_name(
                self.project_name, self.task_name, model_name)
        upnodes = list(up_model_serving_svc.keys())
        responses = asyncMsg([
            "http://{}:{}/predictions/{}".format(
                up_model_serving_svc[model_name], inference_port, model_name)
            for model_name in upnodes
        ], data, 3, False, False)
        return upnodes, responses

    def handle(self, data, context):
        """进行model的预测
        1. 根据数据库查询上游模型
        2. 若有，则获取上游模型的输出
        3. 将json解析的数据与上游模型的输出ensemble_outout给到serving函数
        """
        try:
            upnodes, ensemble_predict_outout = self.preprocess(data[0]["body"])
        except Exception as e:
            return [str(e)]
        ensemble_outout = {}
        for i in range(len(upnodes)):
            if ensemble_predict_outout[i][0] != 200:
                return [None]
            else:
                ensemble_outout[upnodes[i]] = json.loads(
                    ensemble_predict_outout[i][1])["prediction"]
        try:
            pred_out = self.cls_instance.serving(
                json_data=data[0]["body"], ensemble_outout=ensemble_outout)
            return [{"prediction": pred_out}]
        except Exception as e:
            return [str(e)]
