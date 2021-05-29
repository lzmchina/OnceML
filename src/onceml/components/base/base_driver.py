from typing import Dict, List
import onceml.components.base.base_component as base_component
import onceml.components.base.global_component as global_component
from enum import Enum
import onceml.types.exception as exception
import abc
class BaseDriverRunType(Enum):
    DO='Do'
    CYCLE='Cycle'
class BaseDriver(abc.ABC):
    def __init__(self,component:base_component.BaseComponent,pipeline_root:List[str],d_channels:Dict[str,str],d_artifact:Dict[str,str]) -> None:
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
        
        if component.deploytype==base_component.BaseComponentDeployType.DO.value:
            self._runtype=BaseDriverRunType.DO.value
        elif component.deploytype==base_component.BaseComponentDeployType.CYCLE.value:
            self._runtype=BaseDriverRunType.CYCLE.value
        else:
            raise exception.DeployTypeError('DeployType只能是Do或者Cycle')
        self._component=component
        self._pipeline_root=pipeline_root
        self._d_channels=d_channels
        self._d_artifact=d_artifact
    @abc.abstractmethod
    def run(self):
        '''需要根据框架定义具体的执行逻辑
        '''
        pass
