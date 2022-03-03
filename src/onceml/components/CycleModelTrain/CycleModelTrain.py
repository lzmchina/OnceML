from typing import Dict, List, Tuple

from six import MAXSIZE
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
from .Util import _MIN_INT, getTimestampFilteredFile, getEvalSampleFile, getModelPodLabelValue, getPodIpByLabel, updateModelCheckpointToDb, checkModelList, diffFileList, getModelCheckpointFromDb, getModelDir
from onceml.utils.time import get_timestamp
from queue import Queue
from http.server import BaseHTTPRequestHandler
import onceml.configs.k8sConfig as k8sConfig
import onceml.orchestration.base.pipeline_utils as pipeline_utils
import onceml.utils.k8s_ops as k8s_ops
from onceml.utils.http import asyncMsg, asyncMsgByHost, asyncMsgGet
import onceml.global_config as global_config
import json
from threading import Thread, Lock
import copy
from .ModelDag import getModelNodeList, updateUpStreamNode, getModelNode
from deprecated.sphinx import deprecated


class _executor(BaseExecutor):
    def __init__(self,**args):
        super().__init__(**args)
        self.component_state = {}
        self.ensemble_feedback_queue = Queue()
        """存放上游组件的版本信息"""
        self.up_model_checkpoint = {}  # type:Dict[str,int]
        self.data_dir = ""
        # 同步锁
        self.lock = Lock()

        # 存放收到的计算请求，记录每个组件的timestamp
        self.ensemble_requests = {}
        # 存放发出的计算请求，记录每个组件的timestamp，只有收到的反馈里的timestamp等于记录的tiestamp，才认为是需要的
        self.ensemble_feedback_flag = {}

        # 收到的下游模型的更新请求，每次cycle逻辑，都会去将队列里面要通知的模型取出去通知
        self.down_stream_model_update_queue = Queue()

    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels: Dict[str, channel.Channels] = None,
              input_artifacts: Dict[str, Artifact] = None):
        if len(self.emsemble_models) > 0:
            # 有集成模型，需要先获得这些模型的模型信息
            # 1. 先从数据库里更新state里面上游模型的信息
            # 2. 若第一步只有部分模型有大于-1的checkpoint，就阻塞等待，消费ensemble_feedback_queue队列的数据，来更新state
            logger.info("有集成依赖模型，需要先查询依赖模型的信息")
            self.update_up_model_version()
        model_generator = None
        latest_checkpoint = state["model_checkpoint"]
        current_file_id = state['current_file_id']
        featuring_channels = list(input_channels.values())[0]
        recieved_file_id = featuring_channels["checkpoint"]
        max_timestamp = featuring_channels["max_timestamp"]
        min_timestamp = featuring_channels["min_timestamp"]
        samples_dir = list(input_artifacts.values())[0].url
        if recieved_file_id <= current_file_id:
            logger.info("特征工程的最新file id 没超过current_file_id")
            self.broadcast_model_version()
            return {'checkpoint': state["model_checkpoint"]}
        self.lock.acquire()
        checkpoint_flag = [c == -1 for c in self.up_model_checkpoint.values()]
        self.lock.release()
        if any(checkpoint_flag):
            logger.info("集成模型存在部分没有模型")
            self.broadcast_model_version()
            return {'checkpoint': state["model_checkpoint"]}

        need_train = True
        if latest_checkpoint == -1:  # 第一次训练，无需验证，也没有模型可以恢复
            logger.info("第一次训练，无需验证，也没有模型可以恢复")
        else:  # 需要验证一下旧模型的效果
            logger.info("从{}恢复模型".format(latest_checkpoint))
            model_generator: ModelGenerator = self.model_cls(
                os.path.join(data_dir, 'checkpoints', str(latest_checkpoint)))
            logger.info("现在来验证上一个模型的效果")
            evalfiles_with_prefix, _ = getEvalSampleFile(
                samples_dir, '\d+-\d+.pkl', current_file_id, recieved_file_id)
            # 存放依赖的模型的目录，供组件进行模型的加载
            ensemble_model_dirs = {}
            self.lock.acquire()
            model_checkpoints = self.up_model_checkpoint.items()
            self.lock.release()
            for model, c in model_checkpoints:
                ensemble_model_dirs[model] = getModelDir(
                    self.component_msg["task_name"], model, c)
            try:
                need_train = model_generator.eval(evalfiles_with_prefix,
                                                  ensemble_model_dirs)
            except Exception as e:
                logger.error(e)
                self.broadcast_model_version()
                return {'checkpoint': state["model_checkpoint"]}
        if need_train:
            logger.info("现在来训练模型")
            known_results = []
            best_model = None
            beat_metrics = _MIN_INT
            for _ in range(params['max_trial']):
                model_generator = None
                if latest_checkpoint == -1:
                    model_generator: ModelGenerator = self.model_cls(None)
                else:
                    model_generator: ModelGenerator = self.model_cls(
                        os.path.join(data_dir, 'checkpoints', str(latest_checkpoint)))
                start_timestamp, end_timestamp = model_generator.filter(
                    known_results=known_results, time_scope=(min_timestamp, max_timestamp))
                try:
                    matrics = self.standalone_train(
                        model_generator=model_generator,
                        samples_dir=samples_dir,
                        recieved_file_id=recieved_file_id,
                        data_dir=data_dir,
                        params=params,
                        start_timestamp=start_timestamp,
                        end_timestamp=end_timestamp)
                    if matrics != None:
                        known_results.append((start_timestamp, end_timestamp, matrics))
                        if matrics > beat_metrics:
                            beat_metrics = matrics
                            best_model = model_generator
                    else:
                        best_model = model_generator
                        break
                except Exception as e:
                    logger.error(e)
                    continue
            if best_model is None:
                logger.error("没有可用的模型产生")
                self.broadcast_model_version()
                return {'checkpoint': state["model_checkpoint"]}
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
        #os.makedirs(os.path.join(data_dir, 'ensemble_results'), exist_ok=True)
        # 在数据库里注册组件的信息
        pipeline_utils.update_pipeline_model_component_id(
            project_name=self.component_msg['project'],
            task_name=self.component_msg['task_name'],
            model_name=self.component_msg['model_name'],
            model_component_id=self.component_msg['component_id'])

        self.component_state = state  # 访问组件状态需要
        self.lock.acquire()
        for up_model in self.emsemble_models:
            self.up_model_checkpoint[up_model] = -1
        self.lock.release()
        """
        最开始的up model的 checkpoint都是-1
        1. 在pre_execute阶段会向up model所在的组件发送查询，得到能够响应的模型的版本信息
        2. 在Cycle阶段，如果up_model_checkpoint里面有==-1的模型，需要阻塞，直到全部为>-1的值
        """
        self.update_up_model_version()
        """再将自身的模型信息传送给下游模型
        主要从以下情况考虑：可能下游模型存储本模型的版本为100，然后本pipeline重新部署，且
        changed标识位为true，那么就会清除模型，这时需要通知下游组件我的checkpoint已经变了
        """
        self.broadcast_model_version()

    def broadcast_model_version(self):
        """向下游模型训练组件广播自己的checkpoint
        """
        cur = getModelNode(
            self.component_msg['task_name'], self.component_msg['model_name'])
        if cur is None:
            raise RuntimeError("模型{}在模型依赖图里没有对应的节点".format(
                self.component_msg['model_name']))
        down_models = [node.model_name for node in cur.down_models]
        model_pod_label = getModelPodLabelValue(self.component_msg['task_name'],
                                                down_models)
        model_hosts: dict[str, str] = getPodIpByLabel(
            model_pod_label, self.component_msg['resource_namespace'])
        logger.info("要广播的model host：{}".format(model_hosts))
        self.lock.acquire()
        data = {
            "model": self.component_msg['model_name'],
            "checkpoint": self.component_state["model_checkpoint"]
        }
        self.lock.release()
        responses = asyncMsg([
            "http://{}:{}/feedbackv2".format(ip,
                                             global_config.SERVERPORT)
            for ip in list(model_hosts.values())
        ], data, 3, False)
        success_list = []
        for status, jsondata in responses:
            if status == 200:
                success_list.append(jsondata["model"])
        logger.info("成功通知:{}".format(",".join(success_list)))

    def update_up_model_version(self):
        """更新上游模型的当前版本
        1. 通过get的http请求查询组件的接口，如果返回结果，说明该模型的pipeline正在运行，得到的checkpoint也是最新的
        2. 第一步之后，可能部分模型获取不到结果，说明对应的pipeline还没开始运行，或者运行过但结束了，这时可以从数据库里进行更新
        """

        model_pod_label = getModelPodLabelValue(self.component_msg['task_name'],
                                                self.emsemble_models)
        model_hosts: dict[str, str] = getPodIpByLabel(
            model_pod_label, self.component_msg['resource_namespace'])
        logger.info("要更新模型版本的model host：{}".format(model_hosts))

        responses = asyncMsgGet([
            "http://{}:{}/version".format(ip,
                                          global_config.SERVERPORT)
            for ip in list(model_hosts.values())
        ], 3, False)
        success_list = []
        for status, jsondata in responses:
            if status == 200:
                self.lock.acquire()
                self.up_model_checkpoint[jsondata["model"]] = jsondata["checkpoint"]
                self.lock.release()
                success_list.append(jsondata["model"])
        for model in self.emsemble_models:
            if model not in success_list:
                checkpoint = getModelCheckpointFromDb(
                    self.component_msg['task_name'],
                    model)
                self.lock.acquire()
                self.up_model_checkpoint[model] = checkpoint
                self.lock.release()

    def standalone_train(self, model_generator: ModelGenerator, samples_dir: str, recieved_file_id: str, data_dir: str, params: dict, start_timestamp: int, end_timestamp: int) -> float:
        """进行一次训练，产生一个模型

        当需要训练时，选取一个最佳的时间范围的数据很重要
        """
        ensemble_model_dirs = {}
        self.lock.acquire()
        model_checkpoints = self.up_model_checkpoint.items()
        self.lock.release()
        try:
            for model, c in model_checkpoints:
                ensemble_model_dirs[model] = getModelDir(
                    self.component_msg["task_name"], model, c)
        except Exception as e:
            logger.error("获取模型ModelDir：{},{}出错".format(
                ensemble_model_dirs, model_checkpoints))
            logger.error(e)
            raise e
        try:
            filtered_list_with_prefix, _ = getTimestampFilteredFile(
                samples_dir, '\d+-\d+.pkl', start_timestamp, end_timestamp,
                recieved_file_id)
        except Exception as e:
            logger.error("获取数据集出错")
            logger.error(e)
            raise e
        train_metrics = None
        try:
            train_metrics = model_generator.train(filtered_list_with_prefix,
                                                  ensemble_model_dirs)
        except Exception as e:
            logger.error("训练出错训练无效")
            logger.error(e)
            raise e
        return train_metrics

    def GET_version(self, req_handler: BaseHTTPRequestHandler):
        """返回当前的模型的checkpoint

        """
        req_handler.send_response(200)
        req_handler.send_header('Content-type', 'application/json')
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps({
            "model": self.component_msg["model_name"],
            "checkpoint": self.component_state["model_checkpoint"]
        }).encode("utf-8"))

    def POST_feedbackv2(self, req_handler: BaseHTTPRequestHandler):
        '''负责接受上游模型的反馈
        上游模型在产生一个模型后，会从模型依赖dag图里面查询自己的下游节点，再尝试将自己的版本信息发送至下游组件
        '''
        content_length = int(req_handler.headers['Content-Length'])
        post_data = req_handler.rfile.read(content_length).decode(
            'utf-8')  # <--- Gets the data itself
        msg = dict(json.loads(post_data))
        recieved_model = msg['model']
        recieved_checkpoint = msg['checkpoint']
        logger.info("收到模型：{}的版本广播，其使用的checkpoint为：{}".format(
            recieved_model, recieved_checkpoint))
        req_handler.send_response(200)
        req_handler.send_header('Content-type', 'application/json')
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps({
            "model": self.component_msg["model_name"]
        }).encode("utf-8"))
        self.lock.acquire()
        self.up_model_checkpoint[recieved_model] = recieved_checkpoint
        self.lock.release()

    @deprecated(reason="not use", version="0.0.1")
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
        model_pod_label = getModelPodLabelValue(self.component_msg['task_name'],
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

    @deprecated(reason="not use", version="0.0.1")
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
        model_pod_label = getModelPodLabelValue(self.component_msg['task_name'],
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

    @deprecated(reason="not use", version="0.0.1")
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

    @deprecated(reason="not use", version="0.0.1")
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

    @deprecated(reason="not use", version="0.0.1")
    def queryEnsembleModelInfo(self, model_list: list, resource_namespace: str):
        """查询上游模型的信息

        上游模型有以下状态：

        1. kv数据库里没有模型版本：意味着它的pipeline还没有运行或者正在运行，但没有产生一个版本
        2. kv数据库里有模型版本：可以拿过来直接使用

        针对以上的两种情况

        第一种需要进行注册，告诉上游模型我需要你在产生一个模型后通知我\n
        第二种就可以直接从数据库里获取
        """
        known_models = {}
        unknown_models = []
        for model in model_list:
            checkpoint = getModelCheckpointFromDb(
                self.component_msg['task_name'],
                model)
            if checkpoint != -1:
                known_models[model] = getModelDir(
                    self.component_msg['task_name'], model, checkpoint)
            else:
                unknown_models.append(model)
        return known_models, unknown_models

    @deprecated(reason="not use", version="0.0.1")
    def registeModelCallback(self, unknown_models: List[str], resource_namespace):
        """向unknown_models注册通知

        如果这些model的pipeline不在运行状态，则会间隔性的注册,  并且
        """

        data = {
            "timestamp": get_timestamp(),
            "model": self.component_msg['model_name'],
            "resource_namespace": resource_namespace,
        }
        for model in unknown_models:
            self.ensemble_feedback_flag[model] = data['timestamp']

        while len(unknown_models) > 0:
            model_pod_label = getModelPodLabelValue(self.component_msg['task_name'],
                                                    unknown_models)
            model_hosts: dict[str, str] = getPodIpByLabel(
                model_pod_label, resource_namespace)
            logger.info("要通知的model host：{}".format(model_hosts))
            logger.info('开始向要使用的模型发送消息：{}'.format(data))
            # 开始并发的向unknown_models发送请求，如果有组件长时间没有响应，可以认为其pipeline没有运行
            # 这里是为了保证在注册前，反馈队列里没有未处理的信息
            self.ensemble_feedback_queue.join()
            responses = asyncMsg([
                "http://{}:{}/modelCallback".format(ip,
                                                    global_config.SERVERPORT)
                for ip in list(model_hosts.values())
            ], data, 3, False)
            ensure_model = {}
            for status, json in responses:
                if status == 200 and json["flag"]:
                    ensure_model[json["model"]] = True
            new_models = []
            for model in unknown_models:
                if ensure_model.get(ensure_model, False):
                    continue
                else:
                    new_models.append(model)
            unknown_models = new_models
        logger.info('完成对上游模型的回调注册')

    @deprecated(reason="not use", version="0.0.1")
    def POST_modelCallback(self, req_handler: BaseHTTPRequestHandler):
        """用一个队列不断地接受下游模型发送的注册通知
        """
        content_length = int(req_handler.headers['Content-Length'])
        post_data = req_handler.rfile.read(content_length).decode(
            'utf-8')  # <--- Gets the data itself
        msg = dict(json.loads(post_data))
        logger.info("收到来自{}的注册模型通知".format(msg['model']))
        req_handler.send_response(200)
        req_handler.send_header('Content-type', 'application/json')
        req_handler.end_headers()
        req_handler.wfile.write(json.dumps({
            "model": self.component_msg['model_name'],
            "timestamp": msg['timestamp'],
            "flag": True
        }).encode("utf-8"))
        self.down_stream_model_update_queue.put(
            (msg['model'], msg['timestamp'], msg['resource_namespace']))


class CycleModelTrain(BaseComponent):
    def __init__(self,
                 model_generator_cls: object,
                 feauture_component: BaseComponent,
                 emsemble_models: list = [],
                 max_checkpoint_store=1,
                 max_trial=1,
                 parallel=1,
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

        super().__init__(executor=_executor(parallel=parallel),
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

        logger.info(getModelNodeList(task_name=task_name))
        updateUpStreamNode(
            task_name=task_name,
            model_name=model_name,
            up_stream_models=self._params["emsemble_models"]
        )
        logger.info(getModelNodeList(task_name=task_name))
