from typing import Dict, List
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

import shutil


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
        self._d_channels = d_channels
        self._d_artifact = d_artifact

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
        logger.logger.info('清空文件夹{}'.format(component_dir))
        shutil.rmtree(component_dir)
        os.makedirs(component_dir, exist_ok=True)

    def restore_state(self, component_dir: str):
        '''恢复组件的状态，如果状态文件有的话
        '''

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
                - 如果是Do，则加载依赖的组件的结果，然后执行（这里考虑到可能上次的执行由于意外没完成，方便继续执行），结束后保存state，并向后续节点发送信号
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
        self._uniop = importlib.import_module(uni_op_mudule)
        if type(self._component) == global_component.GlobalComponent:
            logger.logger.info('目前是GlobalComponent')
            self.global_component_run()
        elif isinstance(self._component, base_component.BaseComponent):
            logger.logger.info('目前是BaseComponent的子类')
            if self._component._changed:
                logger.logger.info('组件被修改，重建目录')
                self.clear_component_data(component_dir=os.path.join(
                    global_config.OUTPUTSDIR, self._component.artifact.url))
            else:
                self.restore_state(component_dir=os.path.join(
                    global_config.OUTPUTSDIR, self._component.artifact.url))

        else:
            logger.logger.error('无法识别的组件class')
            sys.exit(1)
