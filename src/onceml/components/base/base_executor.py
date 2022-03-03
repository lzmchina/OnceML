# -*- encoding: utf-8 -*-
'''
@Description	:一个基本的execitor,负责component实际的执行轨迹

@Date	:2021/04/19 10:25:11

@Author	:lzm

@version	:0.0.1
'''
from onceml.types import type_check
from onceml.types.channel import Channels
from onceml.types.artifact import Artifact
from typing import Any, List, Dict, Optional
from onceml.types.state import State
from onceml.utils.json_utils import Jsonable


#from abc import abstractmethod
class BaseExecutor(Jsonable):
    """BaseExecutor,组件实际执行的逻辑

    BaseExecutor接收到组件的params、Channels、Artifact，以及依赖组件的Channels、Artifact

    """

    def __init__(self, parallel=1):
        # 组件的一些全局信息：project,task_name、model_name
        self.component_msg: dict = {}
        self.pod_label_value = ""
        self.parallel = parallel
        pass

    # print(self._type)

    # def __new__(cls):

    #     if (bool(cls.Do==BaseExecutor.Do)==bool(cls.Cycle==BaseExecutor.Cycle)):
    #         raise  SyntaxError('Do与Cycle必须有且只能有一个被重写')
    #     return super().__new__(cls)

    def Do(self,
           state: State,
           params: dict,
           data_dir: str,
           input_channels: Optional[Dict[str, Channels]] = None,
           input_artifacts: Optional[Dict[str, Artifact]] = None) -> Channels:
        """
        description
        ---------
        Do方法就是BaseExecutor的实际执行过程，必须自己重写，比如定制自己的组件

        Do只会执行一次

        Args
        -------
        params (dict):用户运行前确定的参数
        data_dir:提供给用户保存数据用额目录
        input_channels:本组件所依赖的组件的Channels
        input_artifacts：本组件所依赖的组件的Artifact

        Returns
        -------
        Channels：本组件的Channels

        Raises
        -------

        """

        pass

    def pre_execute(self, state: State, params: dict, data_dir: str):
        """供Cycle类型组件使用，因为Cycle组件会循环执行Cycle函数，有一些全局变量只需要初始化一次即可
        Args
        -------
        state:组件的当前状态

        params (dict):用户运行前确定的参数

        data_dir:提供给用户保存数据用额目录


        Returns
        -------
        Channels：本组件的Channels

        Raises
        -------
        """
        pass

    def Cycle(
            self,
            state: State,
            params: dict,
            data_dir,
            input_channels: Optional[Dict[str, Channels]] = None,
            input_artifacts: Optional[Dict[str, Artifact]] = None) -> Channels:
        """
        description
        ---------
        Cycle方法就是BaseExecutor的实际执行过程，必须自己重写，比如定制自己的组件

        Cycle会执行多次

        Args
        -------
        params (dict):用户运行前确定的参数
        data_dir:提供给用户保存数据用额目录
        input_channels:本组件所依赖的组件的Channels
        input_artifacts：本组件所依赖的组件的Artifact

        Returns
        -------
        Channels：本组件的Channels

        Raises
        -------

        """

        pass

    @property
    def type(self):
        return self._type

    def exit_execute(self):
        """执行器结束运行后的逻辑
        用户可能在pre_execute时期开启一些进程，这个时候需要在主进程结束后，将子进程也关闭
        """
        pass

    @property
    def parallel(self):
        """获得组件的并行度
        """
        return self._parallel

    @parallel.setter
    def parallel(self, p):
        """设置组件的并行度
        """
        type_check.check_int_of_range(p, 1)
        self._parallel = p

    def to_json_dict(self):
        json_dict = {}
        for k, v in self.__dict__.items():
            if k in ["_parallel"]:
                json_dict[k] = v
        return json_dict

    @classmethod
    def from_json_dict(cls, dict_data):
        """Convert from dictionary data to an object."""
        instance = cls(parallel=dict_data["_parallel"])
        return instance
