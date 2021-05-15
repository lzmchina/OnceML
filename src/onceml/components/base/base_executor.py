# -*- encoding: utf-8 -*-
'''
@Description	:一个基本的execitor,负责component实际的执行轨迹

@Date	:2021/04/19 10:25:11

@Author	:lzm

@version	:0.0.1
'''
from onceml.types import Channels,Artifact
from typing import List,Dict,Optional
#from abc import abstractmethod
class BaseExecutor:
    """BaseExecutor,组件实际执行的逻辑

    BaseExecutor接收到组件的params、Channels、Artifact，以及依赖组件的Channels、Artifact

    """
    def __init__(self):
        if(self.__class__.Do!=BaseExecutor.Do):
            self._type='Do'
        else:
            self._type='Cycle'
        #print(self._type)
    def __new__(cls):

        if (bool(cls.Do==BaseExecutor.Do)==bool(cls.Cycle==BaseExecutor.Cycle)):
            raise  SyntaxError('Do与Cycle必须有且只能有一个被重写') 
        return super().__new__(cls)
    def Do(self,params:dict,input_channels:Optional[Dict[str,Channels]]=None,input_artifacts:Optional[Dict[str,Artifact]]=None)->Channels:
        """
        description
        ---------
        Do方法就是BaseExecutor的实际执行过程，必须自己重写，比如定制自己的组件

        Do只会执行一次

        Args
        -------
        params (dict):用户运行前确定的参数
        input_channels:本组件所依赖的组件的Channels
        input_artifacts：本组件所依赖的组件的Artifact

        Returns
        -------
        Channels：本组件的Channels

        Raises
        -------
        
        """
        
        pass
    def Cycle(self,params:dict,input_channels:Optional[Dict[str,Channels]]=None,input_artifacts:Optional[Dict[str,Artifact]]=None)->Channels:
        """
        description
        ---------
        Cycle方法就是BaseExecutor的实际执行过程，必须自己重写，比如定制自己的组件

        Cycle会执行多次

        Args
        -------
        params (dict):用户运行前确定的参数
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