# -*- encoding: utf-8 -*-
'''
@Description	:一个基本的component，可以直接运行在一个运行环境里

@Date	:2021/04/19 10:25:11

@Author	:lzm

@version	:0.0.1
'''
from onceml.types import Artifact, Channels, OutputChannel
from typing import List, Optional
from .base_executor import BaseExecutor
from onceml.utils import Jsonable

class BaseComponent(Jsonable):
    """BaseComponent是最基本的组件

    BaseComponent是最基本的组件，更复杂的组件应当继承于他。为了保证组件之间的数据流向，component应当具有channel、artifact；应当具有input属性与output属性；同时，组件要运行，就应当具有一个实际执行的逻辑过程

    总结一下：Channel、Artifact是在运行过程中产生的数据结构；param是在运行前设置好的参数；组件的inputs是依赖的组件，outputs是返回组件的channel、artifact
    """

    def __init__(self, executor: BaseExecutor.__class__, inputs: Optional[List] = None, instance_name: str = None, **args):
        """
        description
        ---------
        一个基本的component就是pipline中的最小单元，各个component存在数据依赖，却又独立运行

        Args
        -------
        inputs (List[BaseComponent]):依赖的组件，假如有的话

        instance_name (str): 给组件取一个名字，会作为id属性（如果未指定，则由系统分配）

        args :自行定义各种参数，component会检查每个参数的type，如果是OutputChannel，就是组件Channel的一个属性，其他则认为是params，返回给组件运行时使用



        Returns
        -------
        None

        Raises
        -------
        TypeError:没有按照给定的参数类型来构造
        """
        self.id = instance_name or ''
        if not issubclass(executor, BaseExecutor):
            raise TypeError('传入的executor不是BaseExecutor class')

        self._dependentComponent: List[BaseComponent] = inputs or []
        for c in self._dependentComponent:
            if not isinstance(c, BaseComponent):
                raise TypeError('inputs必须是BaseComponent类或子类')
        #组件运行前传入的静态参数
        self._params = {}
        #组件运行中产生的动态参数
        self._channel = {}
        for key, value in args.items():
            if type(value) == OutputChannel:  # 组件的Channels
                self._channel[key] = value
            else:  # 组件的params
                self._params[key] = value
        # 初始化Artifact
        self._artifact = Artifact()
        self._state = []

        # 找到依赖的组件后，就该将他们的channel、artifact加入进来，这个具体的由pipline操作
        self._dependentChannels = {}
        self._dependentArtifacts = {}
        # 拿到executor class
        self._executor_cls = executor
        #检查executor class是否只重写了一个函数
        if (bool(self._executor_cls.Do==BaseExecutor.Do)==bool(self._executor_cls.Cycle==BaseExecutor.Cycle)):
            raise  SyntaxError('Do与Cycle必须有且只能有一个被重写') 
        #当前节点的上游节点与下游节点
        self._upstreamComponents = set()
        self._downstreamComponents = set()
    def execute(self):
        """execute就是组件实际运行的逻辑

        从拿到依赖组件（上游组件）的Channels、artifact序列化数据并反序列化，再执行

        executor应该由开发者二次继承开发
        """
        self._executor = self._executor_cls()
        if self._executor is None:
            raise Exception('executor未定义')
        if self._executor._type=='Do':
            self._executor.Do(self._params, input_channels=self._dependentChannels,
                          input_artifacts=self._dependentArtifacts)
        elif self._executor._type=='Cycle':
            self._executor.Cycle(self._params, input_channels=self._dependentChannels,
                          input_artifacts=self._dependentArtifacts)
    @property
    def inputs(self):
        return self._dependentComponent

    @property
    def outputs(self):
        return self._channel
    @property
    def dependentComponent(self):
        return self._dependentComponent
    @property
    def upstreamComponents(self):
        return self._upstreamComponents
    def add_upstream_Components(self,component):
        self._upstreamComponents.add(component)
    
    @property
    def downstreamComponents(self):
        return self._downstreamComponents
    def add_downstream_Components(self,component):
        self._downstreamComponents.add(component)
    
    @property
    def artifact(self):
        """组件产生的数据文件的存放地方

        不同于Channels，artifact用来存放数据文件，这些文件通常借助硬盘来交换
        """
        return self._artifact

    @property
    def id(self):
        """组件的唯一id

        可以由组件的构造函数的instance_name指定，或者由系统分配，组件的id在pipline里唯一
        """
        return self._id
    @property
    def type(self) -> str:
        '''该实例归属于哪个class，包名+class名
        '''
        return self.__class__.get_class_type()
    @property
    def deploytype(self) -> str:
        '''该实例是一次执行还是循环执行

        Do:一次执行结束

        Cycle：循环执行
        '''
        if(self._executor_cls.Do!=BaseExecutor.Do):
            return 'Do'
        else:
            return 'Cycle'
    
    @id.setter
    def id(self, _id: str):
        _id = _id or ''
        if not isinstance(_id, str):
            raise TypeError('组件id必须是str类型')
        if _id =='' :#如果用户没有指定，就用类的名称做id
            #print('component id： ',self.__class__.__name__)
            self._id = self.__class__.__name__
        else:
            self._id=_id
    @classmethod
    def get_class_type(cls) -> str:
        return '.'.join(
        [cls.__module__, cls.__name__])
    def to_json_dict(self):
        json_dict={}
        for k,v in self.__dict__.items():
            if k=='_dependentComponent':
                continue
            if k=='_downstreamComponents':
                json_dict[k]=[component.id for component in v ]
            if k not in ['_downstreamComponents','_upstreamComponents']:
                json_dict[k]=v
        return json_dict