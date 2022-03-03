from http.server import BaseHTTPRequestHandler
import os
import subprocess
import time
from typing import ClassVar, Dict, List, Optional, Tuple
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.orchestration.Workflow.types import PodContainer
from onceml.types.artifact import Artifact
from onceml.types.channel import Channels
from onceml.types.state import State
import onceml.types.channel as channel
import threading
import shutil
from onceml.templates import ModelServing
import json
from onceml.utils.logger import logger
from onceml.thirdParty.PyTorchServing import run_ts_serving, outputMar
from onceml.thirdParty.PyTorchServing import TS_PROPERTIES_PATH, TS_INFERENCE_PORT, TS_MANAGEMENT_PORT
from .Utils import generate_onceml_config_json, queryModelIsExist, registerModelJob, get_handler_path, get_handler_module
import pathlib
from onceml.utils.json_utils import objectDumps
import onceml.global_config as global_config
import onceml.orchestration.base.pipeline_utils as pipeline_utils
from deprecated.sphinx import deprecated
from onceml.types.component_msg import Component_Data_URL


class _executor(BaseExecutor):
    def __init__(self, **args):
        super().__init__(**args)
        self.ensemble_models = []
        '''
        model serving template class
        '''
        self.model_serving_cls = None
        self.lock = threading.Lock()
        # 当前正在serving的实例
        self.model_serving_instance: ModelServing = None
        self._ts_process = None
        self.model_timer_thread = None

    @property
    def ts_process(self) -> subprocess.Popen:
        """获得当前的ts serving的Popen实例
        """
        return self._ts_process

    @ts_process.setter
    def ts_process(self, process: subprocess.Popen):
        """设置ts serving的Popen
        """
        self._ts_process = process

    def Cycle(self, state: State, params: dict, data_dir, input_channels: Optional[Dict[str, Channels]] = None, input_artifacts: Optional[Dict[str, Artifact]] = None) -> Channels:
        training_channels = list(input_channels.values())[0]
        latest_checkpoint = state["model_checkpoint"]
        if training_channels["checkpoint"] <= latest_checkpoint:
            # 尝试提交最新的model
            if not queryModelIsExist(self.component_msg["model_name"]):
                mar_file = os.path.join(
                    data_dir, "{}-{}.mar".format(self.component_msg["model_name"], str(state["model_checkpoint"])))
                if os.path.exists(mar_file):
                    if not registerModelJob(
                        url=os.path.abspath(mar_file),
                        handler=get_handler_module()
                    ):
                        logger.error("register failed")
            return None
        to_use_model_dir = os.path.join(list(input_artifacts.values())[
                                        0].url, "checkpoints", str(training_channels["checkpoint"]))
        os.makedirs(data_dir, exist_ok=True)
        # 打包.mar文件
        if not outputMar(
                model_name=self.component_msg["model_name"],
                handler=get_handler_path(),
                extra_file="{},{}".format(to_use_model_dir, os.path.join(
                    data_dir, "onceml_config.json")),
                export_path=data_dir,
                version=str(training_channels["checkpoint"])):
            logger.error("outputMar failed")
            return None
        # 将.mar文件重命名
        os.rename(os.path.join(data_dir, "{}.mar".format(
            self.component_msg["model_name"])), os.path.join(data_dir, "{}-{}.mar".format(
                self.component_msg["model_name"], str(training_channels["checkpoint"]))))
        #提交 .mar
        if not registerModelJob(
            url=os.path.abspath(
                os.path.join(data_dir, "{}-{}.mar".format(self.component_msg["model_name"], str(training_channels["checkpoint"])))),
                handler=get_handler_module()):
            logger.error("register failed")
            return None
        state["model_checkpoint"] = training_channels["checkpoint"]
        return None

    @deprecated(reason="not use", version="0.0.1")
    def register_model_timer(self, state, data_dir):
        '''注册模型的定时器
        现在的torch serving有一些问题：进程莫名退出，这时候pod的相应容器会自动重启，然后需要main容器里的框架定时进行注册
        '''
        def put_model():
            #尝试提交 .mar
            while True:
                # 先查询
                if not queryModelIsExist(self.component_msg["model_name"]):
                    mar_file = os.path.join(
                        data_dir, "{}-{}.mar".format(self.component_msg["model_name"], str(state["model_checkpoint"])))
                    if os.path.exists(mar_file):
                        if not registerModelJob(
                            url=os.path.abspath(mar_file),
                            handler=get_handler_module()
                        ):
                            logger.error("register failed")
                time.sleep(2)
        # 创建线程
        self.model_timer_thread = threading.Thread(target=put_model)

    def pre_execute(self, state: State, params: dict, data_dir: str):
        self.ensemble_models = params["ensemble_models"]
        self.model_serving_cls: type = params["model_serving_cls"]
        # 启动ts serving进程
        # self.ts_process = run_ts_serving(
        #     TS_PROPERTIES_PATH, model_store=os.path.abspath(data_dir))

        initial_mar_file = os.path.join(
            data_dir,
            "{}-{}.mar".format(self.component_msg["model_name"], str(state["model_checkpoint"])))

        if os.path.exists(initial_mar_file):
            # 提交一个.mar文件到ts serving
            if not registerModelJob(url=initial_mar_file, handler=get_handler_module(), maxtry=10):
                logger.error("register failed")
        # 生成handler的runtime 的配置onceml_config.json
        with open(os.path.join(data_dir, "onceml_config.json"), "w") as f:
            f.write(objectDumps(generate_onceml_config_json(
                working_dir=global_config.PROJECTDIR,
                module=self.model_serving_cls.__module__,
                cls_name=self.model_serving_cls.__name__,
                task=self.component_msg["task_name"],
                model=self.component_msg["model_name"],
                project_name=self.component_msg["project"])))
        pipeline_utils.update_pipeline_model_serving_component_id(
            self.component_msg["project"],
            self.component_msg["task_name"],
            self.component_msg["model_name"],
            self.component_msg['component_id'])

    @deprecated(reason="not use", version="0.0.1")
    def exit_execute(self):
        """结束时，也停止响应的ts serving进程
        """
        if self.ts_process is not None:
            self.ts_process.terminate()
            self.ts_process.wait()
            self.ts_process.kill()

    @deprecated(reason="not use", version="0.0.1")
    def _POST_predict(self, req_handler: BaseHTTPRequestHandler):
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
    def __init__(self, model_generator_component: BaseComponent, model_serving_cls, ensemble_models: list = [], parallel=1, **args):
        """部署模型
        接收modelGenerator的更新的模型的消息，从而对部署的模型进行更新
        """
        super().__init__(executor=_executor(parallel=parallel),
                         inputs=[model_generator_component],
                         model_serving_cls=model_serving_cls,
                         ensemble_models=ensemble_models, **args)
        self.state = {
            "model_checkpoint": -1,  # 当前使用的模型的版本号（用模型的时间戳来辨别）
        }

    def extra_pod_containers_user(self,workflow_name) -> List[PodContainer]:
        '''
        注册torch serving
        '''
        ts = PodContainer("ts")
        ts.command = ['python']
        ts.args = ["-m", "onceml.thirdParty.PyTorchServing.initProcess",
                   "--model_store",
                   "{}".format(os.path.join(
                       global_config.OUTPUTSDIR,
                       self.artifact.url,
                       Component_Data_URL.ARTIFACTS.value))]
        ts.SetReadinessProbe([str(TS_INFERENCE_PORT), "/ping"])
        ts.SetLivenessProbe([str(TS_INFERENCE_PORT), "/ping"])
        return [ts]

    def extra_svc_port_user(self) -> List[Tuple[str, str, int]]:
        return [("ts", "TCP", TS_INFERENCE_PORT)]
