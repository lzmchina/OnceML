from typing import Dict, List, Tuple
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.templates import ModelGenerator
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
from onceml.utils.http import asyncMsg, asyncMsgByHost
import onceml.global_config as global_config
import json
from threading import Thread, Lock
import copy
from .ModelDag import getModelNodeList, updateUpStreamNode


class _executor(BaseExecutor):
    def __init__(self):
        super().__init__()
        self.component_state = {}
        self.ensemble_feedback_queue = Queue()
        self.data_dir = ""
        # 存放收到的计算请求，记录每个组件的timestamp
        self.ensemble_requests = {}
        # 存放发出的计算请求，记录每个组件的timestamp，只有收到的反馈里的timestamp等于记录的tiestamp，才可以
        self.ensemble_feedback_flag = {}
        # 同步锁
        self.lock = Lock()

    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels: Dict[str, channel.Channels] = None,
              input_artifacts: Dict[str, Artifact] = None):
        model_generator = None
        latest_checkpoint = state["model_checkpoint"]
        current_file_id = state['current_file_id']
        featuring_channels = list(input_channels.values())[0]
        recieved_file_id = featuring_channels["checkpoint"]
        max_timestamp = featuring_channels["max_timestamp"]
        min_timestamp = featuring_channels["min_timestamp"]
        if recieved_file_id <= current_file_id:
            logger.info("特征工程的最新file id 没超过current_file_id")
            return {'checkpoint': state["model_checkpoint"]}
        if latest_checkpoint == -1:  # 第一次训练，无需验证，也没有模型可以恢复
            logger.info("第一次训练，无需验证，也没有模型可以恢复")
            model_generator: ModelGenerator = self.model_cls(None)
        else:
            logger.info("从{}恢复模型".format(latest_checkpoint))
            model_generator: ModelGenerator = self.model_cls(
                os.path.join(data_dir, 'checkpoints', str(latest_checkpoint)))
        samples_dir = list(input_artifacts.values())[0].url

        need_train = True
        if latest_checkpoint != -1:  # 需要验证一下旧模型的效果
            logger.info("现在来验证上一个模型的效果")
            evalfiles_with_prefix, evalfiles = getEvalSampleFile(
                samples_dir, '\d+-\d+.pkl', current_file_id, recieved_file_id)
            ensemble_model_files = {}
            if len(self.emsemble_models) > 0:
                # 有集成模型，需要先获得这些模型的输出结果文件
                logger.info("有集成依赖模型，需要先传递消息")
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
                # 会block住，直到集成的模型全部完成

                for _ in self.emsemble_models:
                    model, checkpoint = self.ensemble_feedback_queue.get()
                    ensemble_model_files[model] = [
                        os.path.join(data_dir, 'ensemble_results', model,
                                     checkpoint, file) for file in evalfiles
                    ]
                    self.ensemble_feedback_queue.task_done()
            need_train = model_generator.eval(evalfiles_with_prefix,
                                              ensemble_model_files)

        if need_train:
            logger.info("现在来训练模型")
            known_results = []
            best_model = None
            beat_metrics = None
            for i in range(params['max_trial']):
                start_timestamp, end_timestamp = model_generator.filter(
                    known_results=known_results, time_scope=(min_timestamp, max_timestamp))
                model_generator_copy = copy.deepcopy(model_generator)
                matrics = self.standalone_train(
                    model_generator=model_generator_copy,
                    samples_dir=samples_dir,
                    recieved_file_id=recieved_file_id,
                    data_dir=data_dir,
                    params=params,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp)
                if matrics != None:
                    known_results.append((start_timestamp, end_timestamp, matrics))
                    if beat_metrics is None:
                        beat_metrics = matrics
                        best_model = model_generator_copy
                    else:
                        if matrics > beat_metrics:
                            beat_metrics = matrics
                            best_model = model_generator_copy
                else:
                    best_model = model_generator_copy
                    break
            if best_model is None:
                raise Exception("没有可用的模型产生")
            new_checkpoint = str(get_timestamp())
            new_checkpoint_dir = os.path.join(data_dir, 'checkpoints',
                                              new_checkpoint)
            os.makedirs(new_checkpoint_dir, exist_ok=True)
            best_model.model_save(new_checkpoint_dir)
            state['current_file_id'] = recieved_file_id
            state["model_checkpoint"] = new_checkpoint
            updateModelCheckpointToDb(self.component_msg['task_name'],
                                      self.component_msg['model_name'],
                                      new_checkpoint)

        return {'checkpoint': state["model_checkpoint"]}

    def pre_execute(self, state: State, params: dict, data_dir: str):
        logger.info('this is pre_execute')
        self.model_cls: object = params["model_generator_cls"]
        self.emsemble_models = params['emsemble_models']
        self.max_checkpoint_store = params['max_checkpoint_store']
        self.data_dir = data_dir
        self.ensemble_feedback_queue = Queue(maxsize=len(self.emsemble_models))
        os.makedirs(os.path.join(data_dir, 'checkpoints'), exist_ok=True)
        # 创建存放集成模型的输出结果
        os.makedirs(os.path.join(data_dir, 'ensemble_results'), exist_ok=True)
        # 在数据库里注册组件的信息
        pipeline_utils.update_pipeline_model_component_id(
            project_name=self.component_msg['project'],
            task_name=self.component_msg['task_name'],
            model_name=self.component_msg['model_name'],
            model_component_id=self.component_msg['component_id'])

        self.component_state = state  # 访问组件状态需要

    def standalone_train(self, model_generator: ModelGenerator, samples_dir: str, recieved_file_id: str, data_dir: str, params: dict, start_timestamp: int, end_timestamp: int) -> float:
        """进行一次训练，产生一个模型

        当需要训练时，选取一个最佳的时间范围的数据很重要
        """
        ensemble_model_files = {}

        filtered_list_with_prefix, filtered_list = getTimestampFilteredFile(
            samples_dir, '\d+-\d+.pkl', start_timestamp, end_timestamp,
            recieved_file_id)

        if len(self.emsemble_models) > 0:
            # 有集成模型，需要先获得这些模型的输出结果文件
            logger.info("有集成模型，需要先获得这些模型的输出结果文件")
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
            # 会block住，直到集成的模型全部完成
            for _ in self.emsemble_models:
                model, checkpoint = self.ensemble_feedback_queue.get()
                ensemble_model_files[model] = [
                    os.path.join(data_dir, 'ensemble_results', model,
                                 checkpoint, file)
                    for file in filtered_list
                ]
                self.component_state["ensemble_model_checkpoint"][model] = checkpoint
                self.ensemble_feedback_queue.task_done()
        train_metrics = None
        try:
            train_metrics = model_generator.train(filtered_list_with_prefix,
                                                  ensemble_model_files)
        except Exception as e:
            logger.info("训练出错训练无效")
            logger.error(e)
        return train_metrics

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
        data = {
            "timestamp": get_timestamp(),
            "file": file_list,
            "component": self.component_msg['model_name'],
            "save_dir": save_dir,
            "resource_namespace": resource_namespace,
            "samples_dir": samples_dir
        }
        for model in need_use_model:
            self.ensemble_feedback_flag[model] = data['timestamp']
        need_again_send = True
        while need_again_send:
            model_hosts: dict[str,
                              str] = getPodIpByLabel(model_pod_label,
                                                     resource_namespace)
            logger.info("要通知的model host：{}".format(model_hosts))

            logger.info('开始向要使用的模型发送消息：{}'.format(data))
            # 当集成的所有模型都已经完成，就会往这个队列塞一个元素，使得阻塞的线程能够继续
            # logger.info("现在队列里元素个数".format(
            #     self.ensemble_feedback_queue.all_tasks_done()))
            self.ensemble_feedback_queue.join()
            try:
                asyncMsg([
                    "http://{}:{}/calculate".format(ip,
                                                    global_config.SERVERPORT)
                    for ip in list(model_hosts.values())
                ], data, 3)
                need_again_send = False
            except:
                logger.error("发送失败")

    def calculate(self, msg: dict):
        '''实际的集成处理
        因为模型的训练是一个长时过程，在收到计算请求后，需要立即响应http请求，再开一个线程进行计算
        '''
        request_component = msg['component']
        precess_file = msg['file']
        save_dir = msg['save_dir']
        resource_namespace = msg["resource_namespace"]
        timestamp = msg['timestamp']
        samples_dir = msg['samples_dir']
        response_data = {}
        current_checkpoint = self.component_state['model_checkpoint']
        if current_checkpoint == -1:
            # 说明并没有一个模型（其实能够收到请求，说明model_checkpoint已经是大于-1了）
            response_data = {
                "flag": False,
                "component": self.component_msg['model_name'],
                "checkpoint": current_checkpoint,
                "timestamp": timestamp
            }

        else:
            # 只会创建在自己的目录里

            predict_output_dir = os.path.join(save_dir,
                                              self.component_msg['model_name'],
                                              current_checkpoint)
            os.makedirs(predict_output_dir, exist_ok=True)
            # 再看这个目录是否已经有存在的输出文件，可能有些时候会收到多个请求，这时可以对比列表，然后只运行那些没有的文件
            final_files = diffFileList(
                os.path.join(save_dir, self.component_msg['model_name'],
                             current_checkpoint),
                pickle.load(open(precess_file, "rb")))
            model_generator: ModelGenerator = self.model_cls(
                os.path.join(self.data_dir, 'checkpoints',
                             str(current_checkpoint)))
            model_generator.predict(samples_dir, final_files,
                                    predict_output_dir)
            response_data = {
                "flag": True,
                "component": self.component_msg['model_name'],
                "checkpoint": current_checkpoint,
                "timestamp": timestamp
            }
        model_pod_label = getPodLabelValue(self.component_msg['task_name'],
                                           [request_component])
        need_again_send = True
        while need_again_send:
            model_hosts: dict[str,
                              str] = getPodIpByLabel(model_pod_label,
                                                     resource_namespace)
            logger.info("要反馈的model host：{}".format(model_hosts))
            try:
                asyncMsg([
                    "http://{}:{}/feedback".format(ip,
                                                   global_config.SERVERPORT)
                    for ip in list(model_hosts.values())
                ], response_data)
                need_again_send = False
            except:
                logger.error("发送失败")

    def POST_calculate(self, req_handler: BaseHTTPRequestHandler):
        '''负责接受其他模型的请求，对file list进行计算
        '''
        content_length = int(req_handler.headers['Content-Length'])
        post_data = req_handler.rfile.read(content_length).decode(
            'utf-8')  # <--- Gets the data itself
        msg = dict(json.loads(post_data))
        logger.info("收到来自{}的计算请求".format(msg['component']))
        request_component = msg['component']

        timestamp = msg['timestamp']
        before_checkpoint = self.ensemble_requests.get(request_component, None)
        if before_checkpoint is None:
            self.ensemble_requests[request_component] = timestamp
            Thread(target=self.calculate, args=(msg, )).start()
        else:
            if before_checkpoint < timestamp:
                # 说明是新的计算请求，而不是因为组件的重发机制收到的重复计算请求
                self.ensemble_requests[request_component] = timestamp
                Thread(target=self.calculate, args=(msg, )).start()
            else:
                logger.warning("收到重复的计算请求，忽略")
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
        recieved_timestamp = msg['timestamp']
        logger.info("收到{}的计算完成回复，其使用的checkpoint为：{}".format(
            recieved_component, recieved_checkpoint))
        if self.ensemble_feedback_flag[
                recieved_component] != recieved_timestamp:
            logger.error("收到的计算反馈与当初发送的timestamp不一致")
        else:
            self.ensemble_feedback_queue.put(
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
                 max_trial=1,
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
                         max_trial=max_trial,
                         **args)
        self.state = {
            "current_file_id": -1,  # 只对验证有作用
            "model_checkpoint": -1,
            "ensemble_model_checkpoint": {},
        }
        for model in emsemble_models:
            # 记录下依赖的模型的版本
            # 只有在收到feedback后，才会更新这个时间戳
            self.state['ensemble_model_checkpoint'][model] = -1

    def static_check(self, task_name: str, model_name: str):
        """
        将依赖的模型加入到一个图之中，每个task会有一个模型依赖图DAG
        """
        
        print(getModelNodeList(task_name=task_name))
        updateUpStreamNode(
            task_name=task_name, 
            model_name=model_name, 
            up_stream_models=self._params["emsemble_models"]
        )
        print(getModelNodeList(task_name=task_name))
