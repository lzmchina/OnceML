import json
from typing import Any, Dict, List
import onceml.components.base.base_component as base_component
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


class BaseDriverRunType(Enum):
    DO = 'Do'
    CYCLE = 'Cycle'


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

    def global_component_run(self):
        """GlobalComponent的运行
        description
        ---------
        
        Args
        -------
        
        Returns
        -------
        
        Raises
        -------
        
        """

        pass

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
        #系统的pre_execute
        #step 1 ：启动http服务器
        
        #用户自定义的pre_execute逻辑
        self._executor.pre_execute()


    def execute(self, input_channels: Dict[str, Channels],
                input_artifacts: Dict[str, Artifact]):
        """execute就是组件实际运行的逻辑

        从拿到依赖组件（上游组件）的Channels、artifact序列化数据并反序列化，再执行

        executor应该由开发者二次继承开发
        """
        #先来保存下状态
        self._component.state.dump()
        return self._executor_func(state=self._component.state,
                                   params=self._component._params,
                                   input_channels=input_channels,
                                   input_artifacts=input_artifacts)

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
        #先获取上游节点中的Do类型的结果，因为这些都是已经确定的
        Do_Channels, Do_Artifacts = self.get_upstream_component_Do_type_result(
        )
        #确保arifact目录存在
        os.makedirs(
            os.path.join(global_config.OUTPUTSDIR,
                         self._component.artifact.url,
                         Component_Data_URL.ARTIFACTS.value))
        #Cycle类型的组件，现在已经可以运行了
        pipeline_utils.change_components_phase_to_running(
            self._pipeline_id, self._component.id)
        #获取component定义的运行结果字段的类型
        channel_types = self._component._channel
        if self._runtype == BaseDriverRunType.DO.value:

            channel_result = self.execute(Do_Channels, Do_Artifacts)  #获得运行的结果
            #再对channel_result里的结果进行数据校验，只要channel_types里的字段
            validated_channels = self.data_type_validate(
                types_dict=channel_types, data=channel_result)
            #将结果保存
            self.store_channels(validated_channels)
            #将state保存
            self._component.state.dump()
            #运行完成后，更新数据库里的component状态
            pipeline_utils.change_components_phase_to_finished(
                self._pipeline_id, self._component.id)
        else:
            #首先是系统与用户自定义的pre_execute逻辑
            self.pre_execute_cycle()
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
        shutil.rmtree(component_dir)
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
        Do_Artifacts = {}
        for upstream_component in self._component._upstreamComponents:
            #先看看Do_Channels Do_Artifacts与_upstreamComponents对应的组件
            key = upstream_component
            jsonfile = self._d_channels[key]
            Do_Channels[key] = Channels(data=json.load(
                open(os.path.join(global_config.OUTPUTSDIR, jsonfile), 'r')))
            Do_Artifacts[key] = Artifact(url=os.path.join(
                global_config.OUTPUTSDIR, self._d_artifact[key]))
        return Do_Channels, Do_Artifacts

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
        #将pipeline的状态更新只running
        pipeline_utils.change_pipeline_phase_to_running(self._pipeline_id)
        self._uniop = importlib.import_module(uni_op_mudule)
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
                    try:  #尝试转化
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
