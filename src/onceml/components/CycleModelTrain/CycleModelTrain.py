from typing import Dict, List
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.templates.ModelGenerator import ModelGenerator
from onceml.types.state import State
import time
import os
import re
from onceml.utils.logger import logger
import shutil
from types import FunctionType, GeneratorType
import sys
import pickle
import onceml.types.exception as exception
import onceml.types.channel as channel
from onceml.types.artifact import Artifact
from onceml.utils.dir_utils import getLatestTimestampDir
from .Util import getTimestampFilteredFile, getEvalSampleFile, getPodLabelValue, getPodIpByLabel, updateModelCheckpointToDb, checkModelList, diffFileList
from onceml.utils.time import get_timestamp
from queue import Queue
from http.server import BaseHTTPRequestHandler
import onceml.configs.k8sConfig as k8sConfig
import onceml.utils.pipeline_utils as pipeline_utils
import onceml.utils.k8s_ops as k8s_ops
from onceml.utils.http import asyncMsgByHost
import onceml.global_config as global_config
import json
from threading import Thread, Lock


class _executor(BaseExecutor):
    def __init__(self):
        super().__init__()
        self.component_state = {}
        self.ensemble_feedback_flag = Queue()
        self.data_dir = ""
        #存放收到的计算请求，记录每个组件的timestamp
        self.ensemble_requests = {}
        #同步锁
        self.lock = Lock()

    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels: Dict[str, channel.Channels] = None,
              input_artifacts: Dict[str, Artifact] = None):
        model_generator = None
        latest_checkpoint = state["model_checkpoint"]
        if latest_checkpoint == -1:  #第一次训练，无需验证，也没有模型可以恢复
            model_generator: ModelGenerator = self.model_cls(None)
        else:
            model_generator: ModelGenerator = self.model_cls(
                os.path.join(data_dir, 'checkpoints', str(latest_checkpoint)))
        samples_dir = list(input_artifacts.values())[0].url

        need_train = True
        if latest_checkpoint != -1:  #需要验证一下旧模型的效果
            current_file_id = state['current_file_id']
            evalfiles_with_prefix, evalfiles = getEvalSampleFile(
                samples_dir, '\d+-\d+.pkl', current_file_id,
                list(input_channels.values())[0]["checkpoint"])
            ensemble_model_files = {}
            if len(self.emsemble_models) > 0:
                #有集成模型，需要先获得这些模型的输出结果文件
                pickle.dump(
                    evalfiles,
                    open(os.path.join(data_dir, "evalfiles.pkl"), 'wb'))
                self.advice_ensemble_model(
                    model_list=params['emsemble_models'],
                    file_list=os.path.join(data_dir, "evalfiles.pkl"),
                    resource_namespace=self.
                    component_msg['resource_namespace'],
                    save_dir=os.path.join(data_dir, 'ensemble_results'),
                    samples_dir=samples_dir)
                #h会block住，直到集成的模型全部完成

                for _ in self.emsemble_models:
                    model, checkpoint = self.ensemble_feedback_flag.get()
                    ensemble_model_files[model] = [
                        os.path.join(data_dir, 'ensemble_results', model,
                                     checkpoint, file) for file in evalfiles
                    ]
            need_train = model_generator.eval(evalfiles_with_prefix,
                                              ensemble_model_files)
            state['current_file_id'] = list(
                input_channels.values())[0]["checkpoint"]
        if need_train:
            ensemble_model_files = {}
            start_timestamp, end_timestamp = model_generator.filter()
            filtered_list = getTimestampFilteredFile(
                samples_dir, '\d+-\d+.pkl', start_timestamp, end_timestamp,
                list(input_channels.values())[0]["checkpoint"])

            if len(self.emsemble_models) > 0:
                #有集成模型，需要先获得这些模型的输出结果文件
                pickle.dump(
                    filtered_list,
                    open(os.path.join(data_dir, "trainfiles.pkl"), 'wb'))
                self.advice_ensemble_model(
                    model_list=params['emsemble_models'],
                    file_list=os.path.join(data_dir, "trainfiles.pkl"),
                    resource_namespace=self.
                    component_msg['resource_namespace'],
                    save_dir=os.path.join(data_dir, 'ensemble_results'),
                    samples_dir=samples_dir)
                #h会block住，直到集成的模型全部完成

                for _ in self.emsemble_models:
                    model, checkpoint = self.ensemble_feedback_flag.get()
                    ensemble_model_files[model] = [
                        os.path.join(data_dir, 'ensemble_results', model,
                                     checkpoint, file)
                        for file in filtered_list
                    ]
                    state["ensemble_model_checkpoint"][model] = checkpoint
            model_generator.train(filtered_list, ensemble_model_files)
            new_checkpoint = get_timestamp()
            new_checkpoint_dir = os.path.join(data_dir, 'checkpoints',
                                              new_checkpoint)
            os.makedirs(new_checkpoint_dir, exist_ok=True)
            model_generator.model_save(new_checkpoint_dir)
            state["model_checkpoint"] = new_checkpoint
            updateModelCheckpointToDb(self.component_msg['task_name'],
                                      self.component_msg['model_name'],
                                      new_checkpoint)

        return {'checkpoint': state["model_checkpoint"]}

    def pre_execute(self, state: State, params: dict, data_dir: str):
        print('this is pre_execute')
        self.model_cls: object = params["model_generator_cls"]
        self.emsemble_models = params['emsemble_models']
        self.max_checkpoint_store = params['max_checkpoint_store']
        self.data_dir = data_dir
        self.ensemble_feedback_flag = Queue(maxsize=len(self.emsemble_models))
        os.makedirs(os.path.join(data_dir, 'checkpoints'), exist_ok=True)
        #创建存放集成模型的输出结果
        os.makedirs(os.path.join(data_dir, 'ensemble_results'), exist_ok=True)
        #在数据库里注册组件的信息
        pipeline_utils.update_pipeline_model_component_id(
            preject_name=self.component_msg['pipeline_root'],
            task_name=self.component_msg['task_name'],
            model_name=self.component_msg['model_name'],
            model_component_id=self.component_msg['component_id'])

        self.component_state = state  #访问组件状态需要

        #

    def advice_ensemble_model(self, model_list: list, file_list: str,
                              resource_namespace: str, save_dir: str,
                              samples_dir: str):
        '''
        通知ensemble的模型去对file_list文件里的sample进行输出
        
        '''
        need_use_model = checkModelList(
            self.component_msg['task_name'], model_list,
            self.component_state['ensemble_model_checkpoint'])
        #need_use_model = model_list
        model_pod_label = getPodLabelValue(self.component_msg['task_name'],
                                           need_use_model)
        model_hosts: list[str] = getPodIpByLabel(model_pod_label,
                                                 resource_namespace)
        logger.info("要通知的model host：{}".format(model_hosts.__str__))
        data = {
            "timestamp":
            get_timestamp(),
            "file":
            file_list,
            "component":
            pipeline_utils.get_pipeline_model_component_id(
                self.component_msg['task_name'],
                self.component_msg['model_name']),
            "save_dir":
            save_dir,
            "resource_namespace":
            resource_namespace,
            "samples_dir":
            samples_dir
        }
        logger.info('开始向要使用的模型发送消息：{}'.format(data))
        #当集成的所有模型都已经完成，就会往这个队列塞一个元素，使得阻塞的线程能够继续
        self.ensemble_feedback_flag.join()

        asyncMsgByHost([
            "http://{}:{}/calculate".format(ip, global_config.SERVERPORT)
            for ip in model_hosts
        ], data)

    def calculate(self, msg: dict):
        '''实际的集成处理
        因为模型的训练是一个长时过程，在收到计算请求后，需要立即响应http请求，再开一个线程进行计算
        '''
        request_component = msg['component']
        precess_file = msg['file']
        save_dir = msg['save_dir']
        resource_namespace = msg["resource_namespace"]
        timestamp = msg['msg']
        samples_dir = msg['samples_dir']
        response_data = {}
        current_checkpoint = self.component_state['model_checkpoint']
        if current_checkpoint == -1:
            #说明并没有一个模型（其实能够收到请求，说明model_checkpoint已经是大于-1了）
            response_data = {
                "flag": False,
                "component": self.component_msg['model_name'],
                "checkpoint": current_checkpoint
            }

        else:
            #只会创建在自己的目录里

            predict_output_dir = os.path.join(save_dir,
                                              self.component_msg['model_name'],
                                              current_checkpoint)
            os.makedirs(predict_output_dir, exist_ok=True)
            #再看这个目录是否已经有存在的输出文件，可能有些时候会收到多个请求，这时可以对比列表，然后只运行那些没有的文件
            final_files = diffFileList(
                os.path.join(save_dir, self.component_msg['model_name'],
                             current_checkpoint),
                pickle.load(open(precess_file, "rb")))
            model_generator: ModelGenerator = self.model_cls(
                os.path.join(self.data_dir, 'checkpoints',
                             str(current_checkpoint)))
            model_generator.predict(
                [os.path.join(samples_dir, file) for file in final_files],
                predict_output_dir)
            response_data = {
                "flag": True,
                "component": self.component_msg['model_name'],
                "checkpoint": current_checkpoint
            }
        model_pod_label = getPodLabelValue(self.component_msg['task_name'],
                                           [request_component])
        model_hosts: list[str] = getPodIpByLabel(model_pod_label,
                                                 resource_namespace)
        logger.info("要通知的model host：{}".format(model_hosts.__str__))
        asyncMsgByHost([
            "http://{}:{}/feedback".format(ip, global_config.SERVERPORT)
            for ip in model_hosts
        ], response_data)

    def POST_calculate(self, req_handler: BaseHTTPRequestHandler):
        '''负责接受其他模型的请求，对file list进行计算
        '''
        content_length = int(req_handler.headers['Content-Length'])
        post_data = req_handler.rfile.read(content_length).decode(
            'utf-8')  # <--- Gets the data itself
        msg = dict(json.loads(post_data))
        logger.info("收到来自{}的计算请求".format(msg['component']))
        request_component = msg['component']
        precess_file = msg['file']
        save_dir = msg['save_dir']
        resource_namespace = msg["resource_namespace"]
        timestamp = msg['msg']
        samples_dir = msg['samples_dir']
        before_checkpoint = self.ensemble_requests.get(request_component, None)
        if before_checkpoint is None:
            self.ensemble_requests[request_component] = timestamp
        else:
            if before_checkpoint < timestamp:
                #说明是新的计算请求，而不是因为组件的重发机制收到的重复计算请求
                self.ensemble_requests[request_component] = timestamp
                Thread(target=self.calculate, args=(msg,)).start()
        req_handler.send_response(200)
        req_handler.send_header('Content-type', 'application/json')
        req_handler.end_headers()

    def POST_feedback(self, req_handler: BaseHTTPRequestHandler):
        '''负责接受已经完成计算任务的模型的反馈
        '''
        content_length = int(req_handler.headers['Content-Length'])
        post_data = req_handler.rfile.read(content_length).decode(
            'utf-8')  # <--- Gets the data itself

        msg = dict(json.loads(post_data))
        recieved_component = msg['component']
        recieved_checkpoint = msg['checkpoint']
        logger.log("收到{}的计算完成回复，其使用的checkpoint为：{}".format(
            recieved_component, recieved_checkpoint))
        self.ensemble_feedback_flag.put(
            (recieved_component, recieved_checkpoint))
        self.component_state["ensemble_model_checkpoint"][
            recieved_component] = recieved_checkpoint
        req_handler.send_response(200)
        req_handler.send_header('Content-type', 'application/json')
        req_handler.end_headers()


class CycleModelTrain(BaseComponent):
    def __init__(self,
                 model_generator_cls: object,
                 feauture_component: BaseComponent,
                 emsemble_models: list = [],
                 max_checkpoint_store=1,
                 **args):
        """
        description
        ---------   
        CycleModelTrain组件是用来产生一个可用于部署的模型，它会提供sample的url list，用户拿到这些路径后，可以自己定义是一起加载到内存里，还是使用队列
        防止占满内存。然后返回一个模型，供后续的model serving使用

        同时，会提供timestamp筛选的功能，只要这些满足条件的samples

        它还拥有模型集成功能，只需要声明依赖的模型的list，就能自动将sample送至依赖的模型，得到结果

       

        Args
        -------
        model_generator_cls:用来封装功能的类

        feauture_component:特征工程组件
        
        emsemble_models:需要集成的模型列表，例如["modelB","modelC"]

        max_checkpoint_store:最多保存模型的数目
        Returns
        -------
        
        Raises
        -------
        
        """

        super().__init__(executor=_executor,
                         inputs=[feauture_component],
                         checkpoint=channel.OutputChannel(int),
                         model_generator_cls=model_generator_cls,
                         emsemble_models=emsemble_models,
                         max_checkpoint_store=max_checkpoint_store,
                         **args)
        self.state = {
            "current_file_id": -1,  #只对验证有作用
            "model_checkpoint": -1,
            "ensemble_model_checkpoint": {}
        }
        for model in emsemble_models:
            #记录下依赖的模型的版本，当有新版本的模型产生时，才回去用新的模型去获得他们的结果
            #只有在收到feedback后，才会更新这个时间戳
            self.state['ensemble_model_checkpoint'][model] = -1