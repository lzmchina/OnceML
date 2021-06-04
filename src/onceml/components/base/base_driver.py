import json
import time
import grequests

import urllib
from queue import Queue
from typing import Any, Dict, List
import onceml.components.base.base_component as base_component
import onceml.components.base.base_executor as base_executor
import onceml.components.base.global_component as global_component
from enum import Enum
import onceml.types.exception as exception
import abc
import importlib
import os
import sys
import onceml.utils.logger as logger
import onceml.global_config as global_config
import onceml.utils.json_utils as json_utils
import shutil
from onceml.types.component_msg import Component_Data_URL
from onceml.types.channel import Channels, OutputChannel
from onceml.types.artifact import Artifact
from onceml.types.state import State
import onceml.utils.pipeline_utils as pipeline_utils
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import threading
import onceml.orchestration.kubeflow.kfp_ops as kfp_ops
import onceml.utils.time as time_utils
import onceml.types.phases as phases


class BaseDriverRunType(Enum):
    DO = 'Do'
    CYCLE = 'Cycle'


def generate_handler(driver_instance):

    class BaseHandler(BaseHTTPRequestHandler):
        default_request_version = "HTTP/1.1"

        def __init__(self,  *args, **kwargs) -> None:
            self._driver_instance: BaseDriver = driver_instance
            super(BaseHandler, self).__init__(*args, **kwargs)

        def _set_response(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

        def _set_json_response(self):

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

        def add_msg_to_queue(self, json_str: str):
            '''将收到的上游的组件的消息放入对应的消息队列
            '''
            msg = dict(json.loads(json_str))
            compoent_id = msg.pop('component')
            self._driver_instance.add_msg(compoent_id, msg)

        def do_GET(self):
            '''用来充当server的get处理
            '''

            print(self.path)

            #message = "Hello, World! Here is a GET response"
            #self.wfile.write(bytes(message, "utf8"))
            self._set_response()
            self.wfile.write("Hello, World! Here is a GET response".encode('utf-8'))

        def do_POST(self):
            '''用来充当server的post处理
            '''

            # 获取post提交的数据
            # datas = self.rfile.read(int(self.headers['content-length']))
            # datas = urllib.unquote(datas).decode("utf-8", 'ignore')
            # <--- Gets the size of data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode(
                'utf-8')  # <--- Gets the data itself
            self.add_msg_to_queue(post_data)
            self._set_json_response()
            self.wfile.write(json.dumps({'a': 1}).encode('utf-8'))
    return BaseHandler


class BaseDriver(abc.ABC):
    def __init__(self, component: base_component.BaseComponent,
                 pipeline_root: List[str], d_channels: Dict[str, str],
                 d_artifact: Dict[str, str]) -> None:
        """基础类，在每个编排系统里具体执行的逻辑
        description
        ---------
        在拿到组件后，就要负责执行组件的逻辑
        Args
        -------
        component：base_component的子类，也可能是global_component类，二者的执行逻辑不一样

        pipeline_root： 为该组件所属的pipeline的task name 与model name，是一个list

        d_channels: 所依赖的Do类型的结果的json文件路径

        d_artifact：所依赖的组件的数据路径

        Returns
        -------

        Raises
        -------

        """

        if component.deploytype == base_component.BaseComponentDeployType.DO.value:
            self._runtype = BaseDriverRunType.DO.value
        elif component.deploytype == base_component.BaseComponentDeployType.CYCLE.value:
            self._runtype = BaseDriverRunType.CYCLE.value
        else:
            raise exception.DeployTypeError('DeployType只能是Do或者Cycle')
        self._component = component
        self._pipeline_root = pipeline_root
        self._pipeline_id = '.'.join(pipeline_root)
        self._d_channels = d_channels
        self._d_artifact = d_artifact

        self._executor = self._component._executor_cls()
        if self._runtype == BaseDriverRunType.DO.value:
            self._executor_func = self._executor.Do
        else:
            self._executor_func = self._executor.Cycle
        self._upstream_msg_queue: Dict[str, dict] = {}
        # Cycle类型的组件不仅要接收前面的组件的消息，并储存，还要另外的循环执行Cycle逻辑，因此消息的存储与消耗是需要用锁控制的
        self._upstream_msg_queue_lock: threading.Lock = None
        self.server = None

    def global_component_run(self):
        """GlobalComponent的运行
        description
        ---------
        - 如果是Do，则判断其alias的组件的状态是否是finished，直到其finished就跳至{}结束
        - 如果是Cycle，则判断组件的phase是否是running即可就跳至{}退出
        Args
        -------

        Returns
        -------

        Raises
        -------

        """
        # 如果是共享组件，则会建立软链接目录
        if not os.path.exists(
                os.path.join(global_config.OUTPUTSDIR, self._pipeline_root[0],
                             self._component._alias_model_name,
                             self._component._alias_component_id)):
            logger.logger.error('全局组件{}的依赖目录不存在'.format(self._component.id))
            raise exception.FileNotFoundError()
        try:
            os.symlink(src=os.path.join(os.getcwd(),
                                        global_config.OUTPUTSDIR,
                                        self._pipeline_root[0],
                                        self._component._alias_model_name,
                                        self._component._alias_component_id),
                       dst=os.path.join(os.getcwd(),
                                        global_config.OUTPUTSDIR,
                                        self._pipeline_root[0],
                                        self._pipeline_root[1],
                                        self._component.id))
        except FileExistsError:
            logger.logger.warning('全局组件{}的软链接目录已经存在'.format(self._component.id))
        if self._runtype == BaseDriverRunType.DO.value:
            while True:
                phase = pipeline_utils.db_get_pipeline_component_phase(
                    task_name=self._pipeline_root[0],
                    model_name=self._component._alias_model_name,
                    component=self._component
                )
                if phase == phases.Component_PHASES.FINISHED.value:
                    logger.logger.info('组件{}:{} alias的组件{}:{}已经finished，可以退出进程'.format(
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._pipeline_root[1]),
                        self._component.id,
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._component._alias_model_name),
                        self._component._alias_component_id
                    ))
                    break
                else:
                    logger.logger.info('组件{}:{} alias的组件{}:{}没有finished，继续监听'.format(
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._pipeline_root[1]),
                        self._component.id,
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._component._alias_model_name),
                        self._component._alias_component_id
                    ))
                time.sleep(2)
        else:
            while True:
                phase = pipeline_utils.db_get_pipeline_component_phase(
                    task_name=self._pipeline_root[0],
                    model_name=self._component._alias_model_name,
                    component=self._component.id
                )
                if phase == phases.Component_PHASES.RUNNING.value:
                    logger.logger.info('组件{}:{} alias的组件{}:{}正在running，可以退出进程'.format(
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._pipeline_root[1]),
                        self._component.id,
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._component._alias_model_name),
                        self._component._alias_component_id
                    ))
                    break
                else:
                    logger.logger.info('组件{}:{} alias的组件{}:{}没有running，继续监听'.format(
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._pipeline_root[1]),
                        self._component.id,
                        pipeline_utils.generate_pipeline_id(
                            self._pipeline_root[0], self._component._alias_model_name),
                        self._component._alias_component_id
                    ))
                time.sleep(2)

    def pre_execute_cycle(self):
        """在cycle类型组件开始执行cycle之前的pre execute
        description
        ---------
        cycle类型的组件是循环执行的，在一定条件触发后（比方说收到上游组件的结果），就会执行Cycle函数，因此可以执行用户在executor里面自定义的pre_execute逻辑

        Args
        -------

        Returns
        -------

        Raises
        -------

        """
        pass

    def build_msg_queue(self):
        '''为cycle组件构建消息数组，用于接收上游cycle组件的消息，如果有的话
        '''
        self._upstream_msg_queue = {}
        self._upstream_msg_queue_lock = threading.Lock()
        for upstream in self._d_artifact:
            if upstream not in self._d_channels:  # 只考虑上游组件里的Cycle类型
                self._upstream_msg_queue[upstream] = None

    def add_msg(self, key: str, msg_dict: dict):
        '''将某个上游cycle组件传来的消息放入队列里
        '''
        self._upstream_msg_queue_lock.acquire()
        if self._upstream_msg_queue[key] is None:
            self._upstream_msg_queue[key] = msg_dict
        else:
            self._upstream_msg_queue[key] = msg_dict if msg_dict['timestamp'] > self._upstream_msg_queue[
                key]['timestamp'] else self._upstream_msg_queue[key]
        self._upstream_msg_queue_lock.release()
        # self.show_queue()

    def pop_all_msg(self):
        '''获得目前的所有上游cycle类型的消息
        '''
        self._upstream_msg_queue_lock.acquire()
        result = self._upstream_msg_queue.copy()
        for key in self._upstream_msg_queue:
            self._upstream_msg_queue[key] = None
        self._upstream_msg_queue_lock.release()
        return result

    def show_queue(self):
        for key, value in self._upstream_msg_queue.items():
            logger.logger.info('{}:{}'.format(key, value))

    def start_server(self):
        '''为cycle组件启动一个server
        '''
        self.server = HTTPServer(('0.0.0.0', global_config.SERVERPORT),
                                 generate_handler(self))
        logger.logger.info('start server')
        threading.Thread(target=self.server.serve_forever).start()

    def execute(self, input_channels: Dict[str, Channels],
                input_artifacts: Dict[str, Artifact]):
        """execute就是组件实际运行的逻辑

        从拿到依赖组件（上游组件）的Channels、artifact序列化数据并反序列化，再执行

        executor应该由开发者二次继承开发
        """
        # 先来保存下状态
        self._component.state.dump()
        return self._executor_func(state=self._component.state,
                                   params=self._component._params,
                                   data_dir=os.path.join(
                                       global_config.OUTPUTSDIR,
                                       self._component.artifact.url,
                                       Component_Data_URL.ARTIFACTS.value),
                                   input_channels=input_channels,
                                   input_artifacts=input_artifacts)

    def send_channels(self, validated_channels: Dict):
        '''将经过验证的结果发送给后续cycle节点（如果有的话）
        '''
        def err_handler(request, exception):
            logger.logger.error("请求出错")
        # try:
        host_list = self.get_ip_by_label_func(task_name=self._pipeline_root[0],
                                              model_name=self._pipeline_root[1],
                                              component_id=self._component.id)
        logger.logger.info('host_list: {}'.format(host_list))
        # 开始并发式的发送消息
        req_list = [
            grequests.post(
                '{ip}:{port}'.format(
                    ip=host[0],
                    port=host[1]
                    # ip='http://httpbin.org/delay/5'
                ),
                data={
                    'component': self._component.id,  # 标志一下是哪个component发的
                    'timestamp': time_utils.get_timestamp(),  # 写一下数据产生的时间，接收方只需要保存最新的即可，防止两边速度不一致
                    **validated_channels

                },
                timeout=3)  # 3秒的timeout
            for host in host_list
        ]
        res_list = grequests.map(req_list, exception_handler=err_handler)
        logger.logger.info(res_list)
        # except:
        #    logger.logger.error('没有在{}找到get_ip_port_by_label函数'.format(self._uniop))

    def base_component_run(self):
        """普通组件的运行
        description
        ---------

        Args
        -------

        Returns
        -------

        Raises
        -------

        """
        # 先获取上游节点中的Do类型的结果，因为这些都是已经确定的
        Do_Channels, Artifacts = self.get_upstream_component_Do_type_result(
        )
        # 确保arifact目录存在
        os.makedirs(
            os.path.join(global_config.OUTPUTSDIR,
                         self._component.artifact.url,
                         Component_Data_URL.ARTIFACTS.value), exist_ok=True)
        # Cycle类型的组件，现在已经可以运行了
        pipeline_utils.change_components_phase_to_running(
            self._pipeline_id, self._component.id)
        # 获取component定义的运行结果字段的类型
        channel_types = self._component._channel
        if self._runtype == BaseDriverRunType.DO.value:

            channel_result = self.execute(Do_Channels, Artifacts)  # 获得运行的结果
            # 再对channel_result里的结果进行数据校验，只要channel_types里的字段
            validated_channels = self.data_type_validate(
                types_dict=channel_types, data=channel_result)
            # 将结果保存
            self.store_channels(validated_channels)
            # 将state保存
            self._component.state.dump()
            # 运行完成后，更新数据库里的component状态
            pipeline_utils.change_components_phase_to_finished(
                self._pipeline_id, self._component.id)
        else:
            # 首先用户自定义的pre_execute逻辑
            self._executor.pre_execute()
            # 然后再根据组件是否有cycle类型的上游组件来进行后面的操作
            # 如果是没有cycle上游组件，则认为他是信号源，需要不断的执行，并向后发送消息
            # 如果有，则认为他是由前面cycle组件驱动的

            if len(self._d_channels) == len(
                    self._component._upstreamComponents):
                logger.logger.info('该组件是信号源')  # 即没有cycle类型的上游组件
                # 就直接循环执行
                while True:
                    channel_result = self.execute(Do_Channels,
                                                  Artifacts)  # 获得运行的结果
                    # 再对channel_result里的结果进行数据校验，只要channel_types里的字段
                    validated_channels = self.data_type_validate(
                        types_dict=channel_types, data=channel_result)
                    # 将state保存
                    self._component.state.dump()
                    # 将结果发送给后续cycle节点(如果有的话)
                    self.send_channels(validated_channels)

            else:
                logger.logger.info('该组件受到前面组件信号的控制')
                # step 2:构建消息队列缓存区
                self.build_msg_queue()
                # step 3 ：启动http服务器
                self.start_server()
                logger.logger.info('启动server后继续执行')
                while True:
                    # 不断地获取消息
                    Cycle_Channels = self.get_upstream_component_Cycle_type_result()
                    if Cycle_Channels is None:
                        # 如果消息为None，则直接跳过
                        logger.logger.info('暂时没有上游的消息，跳过执行')
                        time.sleep(2)
                        continue
                    channel_result = self.execute({**Do_Channels, **Cycle_Channels},
                                                  Artifacts)  # 获得运行的结果
                    # 再对channel_result里的结果进行数据校验，只要channel_types里的字段
                    validated_channels = self.data_type_validate(
                        types_dict=channel_types, data=channel_result)
                    # 将state保存
                    self._component.state.dump()
                    # 将结果发送给后续cycle节点(如果有的话)
                    self.send_channels(validated_channels)
                    time.sleep(5)

    def clear_component_data(self, component_dir: str):
        """删除组件的数据
        description
        ---------
        组件不需要复用之前的数据，则删除相应的数据

        Args
        -------

        Returns
        -------

        Raises
        -------

        """
        logger.logger.warning('清空文件夹{}'.format(component_dir))
        try:
            shutil.rmtree(component_dir)
        except FileNotFoundError:
            logger.logger.warning('组件{}的目录已经不存在'.format(self._component.id))
        os.makedirs(component_dir, exist_ok=True)

    def restore_state(self, component_dir: str):
        '''恢复组件的状态，如果状态文件有的话
        '''
        state_file = os.path.join(component_dir,
                                  Component_Data_URL.STATE.value)
        if not os.path.exists(state_file):
            logger.logger.warning('{}下没有{}文件，没有状态可以恢复'.format(
                component_dir, Component_Data_URL.STATE.value))

        else:
            self._component.state.load()

    def get_upstream_component_Do_type_result(self):
        """获取上游组件中Do类型的结果与目录
        """
        Do_Channels = {}
        Artifacts = {}
        for upstream_component in self._d_artifact:
            # 先看看Do_Channels Do_Artifacts与_upstreamComponents对应的组件
            if upstream_component in self._d_channels:
                jsonfile = self._d_channels[upstream_component]
                Do_Channels[upstream_component] = Channels(data=json.load(
                    open(os.path.join(global_config.OUTPUTSDIR, jsonfile), 'r')))
            Artifacts[upstream_component] = Artifact(url=os.path.join(
                global_config.OUTPUTSDIR, self._d_artifact[upstream_component]))
        return Do_Channels, Artifacts

    def get_upstream_component_Cycle_type_result(self):
        """获取上游组件中Cycle类型的结果与目录
        """
        Cycle_Channels = {}
        msgs = self.pop_all_msg()
        if not any(msgs.values()):
            logger.logger.info('Cycle_Channels没有消息')
            Cycle_Channels = None
        else:
            for cycleid, msg in msgs.items():
                if msg:
                    msg.pop('timestamp')
                Cycle_Channels[cycleid] = Channels(data=msg)
        return Cycle_Channels

    def run(self, uni_op_mudule: str):
        '''需要根据框架定义具体的执行逻辑
        description
        ---------
        主要逻辑分为以下几步：

        1. 判断driver的component是否是globalcomponent，如果是，则根据他的deploytype进行下一步判断，否则跳至2：
                - 如果是Do，则判断其alias的组件的状态是否是finished，直到其finished就跳至{}结束
                - 如果是Cycle，则判断组件的phase是否是running即可就跳至{}退出
        2. 现在说明都是basecomponent的子类，然后根据component的_changed属性判断是否需要复用之前的数据
                - _changed若为true，则说明组件发生修改，直接删除原来的数据与数据库里的state，重新创建，再跳至3
                - _changed为false，则直接复用之前的数据，并恢复数据库里的state，然后跳至4
        3. 判断_changed为true的deploytype：
                - 如果是Do，则加载依赖的组件的结果，然后执行，结束后保存state，并向后续节点发送信号
                - 如果是Cycle，则在收到依赖节点的信号，然后执行，每次执行完保存state，并向后续节点发送信号
        4. 判断_changed为false的deploytype：
                - 如果是Do，则判断，然后执行（这里考虑到可能上次的执行由于意外没完成，方便继续执行），结束后保存state，并向后续节点中的cycle节点发送信号
                - 如果是Cycle，则在收到依赖节点的信号，然后执行，每次执行完保存state，并向后续节点发送信号
        5. 结束

        Args
        -------
        uni_op_mudule:统一操作接口模块，目前只有kfp这一框架，为了保证拓展性，因为所有的driver处理的逻辑是一致的，但是由于平台特性，有些是不一样的，这些不一样的可以另外设置，只要保证api名称相同即可

        Returns
        -------

        Raises
        -------

        '''
        pipeline_utils.create_pipeline_dir(os.path.join(
            global_config.OUTPUTSDIR,
            self._pipeline_root[0],
            self._pipeline_root[1]
        ))
        # 将pipeline的状态更新只running
        pipeline_utils.change_pipeline_phase_to_running(self._pipeline_id)
        self._uniop = importlib.import_module(uni_op_mudule)
        self.get_ip_by_label_func = getattr(self._uniop, 'get_ip_port_by_label')

        # self._uniop=__import__(uni_op_mudule)
        if type(self._component) == global_component.GlobalComponent:
            # step 1
            logger.logger.info('目前是GlobalComponent')
            self.global_component_run()
        elif isinstance(self._component, base_component.BaseComponent):
            # step 2
            logger.logger.info('目前是BaseComponent的子类')
            self._component._state = State(json_path=os.path.join(
                global_config.OUTPUTSDIR, self._component.artifact.url,
                Component_Data_URL.STATE.value))
            if self._component._changed:
                logger.logger.warning('组件被修改，重建目录')
                self.clear_component_data(component_dir=os.path.join(
                    global_config.OUTPUTSDIR, self._component.artifact.url))

            else:
                logger.logger.info('组件复用之前的数据，并恢复state')
                self.restore_state(component_dir=os.path.join(
                    global_config.OUTPUTSDIR, self._component.artifact.url))
            # step 3,4
            self.base_component_run()
        else:
            logger.logger.error('无法识别的组件class')
            sys.exit(1)

    def data_type_validate(self, types_dict: Dict[str, OutputChannel],
                           data: Dict[str, Any]):
        '''对data字典里的key以及value的type进行校验

        - 针对key，要满足key是声明在types_dict里面

        - 针对value，要满足value的type与types_dict里面定义的符合
        '''
        for key, value in data.items():
            if key in types_dict:
                if type(value) != types_dict[key]:
                    try:  # 尝试转化
                        data[key] = types_dict[key]._type(value)
                    except:
                        raise TypeError('{}的类型为{},且无法强制转化'.format(
                            key, type(value)))
            else:
                data.pop(key)
        return data

    def store_channels(self, validated_channels: Dict[str, Any]):
        """将运行结果保存到result.json
        """
        json.dump(validated_channels,
                  open(
                      os.path.join(global_config.OUTPUTSDIR,
                                   self._component.artifact.url,
                                   Component_Data_URL.CHANNELS.value), 'w'),
                  indent=4)
