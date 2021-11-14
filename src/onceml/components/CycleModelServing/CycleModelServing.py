from http.server import BaseHTTPRequestHandler
import os
from typing import Dict, Optional
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.types.artifact import Artifact
from onceml.types.channel import Channels
from onceml.types.state import State
import onceml.types.channel as channel
import threading
import shutil
from onceml.templates import ModelServing
import json
from onceml.utils.logger import logger

class _executor(BaseExecutor):
    def __init__(self):
        super().__init__()
        self.ensemble_models = []
        '''
        model serving template class
        '''
        self.model_serving_cls = None
        self.lock = threading.Lock()
        # 当前正在serving的实例
        self.model_serving_instance: ModelServing = None

    def Cycle(self, state: State, params: dict, data_dir, input_channels: Optional[Dict[str, Channels]] = None, input_artifacts: Optional[Dict[str, Artifact]] = None) -> Channels:
        tarining_channels = list(input_channels.values())[0]
        latest_checkpoint = state["model_checkpoint"]
        if tarining_channels["checkpoint"] <= latest_checkpoint:
            return None
        state["model_checkpoint"] = tarining_channels["checkpoint"]
        to_use_model_dir = os.path.join(list(input_artifacts.values())[
                                        0].url, "checkpoints", str(state["model_checkpoint"]))
        local_dir = os.path.join(
            data_dir, 'serving_models', str(state["model_checkpoint"]))
        shutil.copytree(to_use_model_dir, local_dir, dirs_exist_ok=True)
        new_model_serving_instance = self.model_serving_cls(local_dir)
        # 这时候需要对实例进行更新
        self.lock.acquire()
        self.model_serving_instance = new_model_serving_instance
        self.lock.release()
        logger.info("完成对model_serving_instance的更新")
        return None

    def pre_execute(self, state: State, params: dict, data_dir: str):
        self.ensemble_models = params["ensemble_models"]
        self.model_serving_cls = params["model_serving_cls"]
        # 创建存放不同时间戳的模型的文件夹，实际是把上一个model train传过来的checkpoint拷贝过来
        os.makedirs(os.path.join(data_dir, 'serving_models'), exist_ok=True)
        if os.path.exists(os.path.join(data_dir, 'serving_models', str(state["model_checkpoint"]))):
            new_model_serving_instance = self.model_serving_cls(
                os.path.join(data_dir, 'serving_models', str(state["model_checkpoint"])))
            # 这时候需要对实例进行更新
            self.lock.acquire()
            self.model_serving_instance = new_model_serving_instance
            self.lock.release()

    def POST_predict(self, req_handler: BaseHTTPRequestHandler):
        content_length = int(req_handler.headers['Content-Length'])
        post_data = req_handler.rfile.read(content_length).decode(
            'utf-8')  # <--- Gets the data itself
        '''todo:add ensemble
        '''
        logger.info("收到predict请求")
        self.lock.acquire()
        use_instance = self.model_serving_instance
        self.lock.release()
        logger.info("获得use_instance")
        if use_instance is None:
        
            req_handler.send_response(200)
            req_handler.send_header('Content-type', 'application/json')
            req_handler.end_headers()
            req_handler.wfile.write("no available model".encode('utf-8'))
        else:
            res = self.model_serving_instance.serving(post_data, None)
            req_handler.send_response(200)
            req_handler.send_header('Content-type', 'application/json')
            req_handler.end_headers()
            req_handler.wfile.write(json.dumps(res).encode('utf-8'))


class CycleModelServing(BaseComponent):
    def __init__(self, model_generator_component: BaseComponent, model_serving_cls, ensemble_models: list = [], **args):
        """部署模型
        接收modelGenerator的更新的模型的消息，从而对部署的模型进行更新
        """
        super().__init__(executor=_executor,
                         inputs=[model_generator_component],
                         model_serving_cls=model_serving_cls,
                         ensemble_models=ensemble_models, **args)
        self.state = {
            "model_checkpoint": -1,  # 当前使用的模型的版本号（用模型的时间戳来辨别）
        }
