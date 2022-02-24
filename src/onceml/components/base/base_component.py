# -*- encoding: utf-8 -*-
'''
@Description	:一个基本的component，可以直接运行在一个运行环境里

@Date	:2021/04/19 10:25:11

@Author	:lzm

@version	:0.0.1
'''
from onceml.types.artifact import Artifact
from onceml.types.channel import Channels, OutputChannel
from onceml.types.state import State
from typing import Any, Dict, List, Optional, Tuple
from .base_executor import BaseExecutor
from onceml.utils.json_utils import Jsonable
import onceml.types.exception as exception
from enum import Enum
from deprecated.sphinx import deprecated
class BaseComponentDeployType(Enum):
    DO = 'Do'
    CYCLE = 'Cycle'
class PodContainer():
    def __init__(self) -> None:
        pass

class BaseComponent(Jsonable):
    """BaseComponent是最基本的组件

    BaseComponent是最基本的组件，更复杂的组件应当继承于他。为了保证组件之间的数据流向，component应当具有channel、artifact；应当具有input属性与output属性；同时，组件要运行，就应当具有一个实际执行的逻辑过程

    总结一下：Channel、Artifact是在运行过程中产生的数据结构；param是在运行前设置好的参数；组件的inputs是依赖的组件，outputs是返回组件的channel、artifact
    """

    def __init__(self,
                 executor: BaseExecutor.__class__,
                 inputs: Optional[List] = None,
                 shared: bool = False,
                 **args):
        """
        description
        ---------
        一个基本的component就是pipleine中的最小单元，各个component存在数据依赖，却又独立运行

        Args
        -------
        inputs (List[BaseComponent]):依赖的组件，假如有的话

        instance_name (str): 给组件取一个名字，会作为id属性（如果未指定，则由系统分配）

        shared(bool):是否会共享组件的数据 (todo)

        args :自行定义各种参数，component会检查每个参数的type，如果是OutputChannel，就是组件Channel的一个属性，只会在组件的cycle或者do函数执行完成后
        对其返回的字典中的key做校验，如果key没有用OutputChannel声明，则会被丢弃
        ;其他则认为是params，返回给组件运行时使用



        Returns
        -------
        None

        Raises
        -------
        TypeError:没有按照给定的参数类型来构造
        """

        if not issubclass(executor, BaseExecutor):
            raise TypeError('传入的executor不是BaseExecutor class')
        if inputs is not None and type(inputs)!=list:
            raise TypeError("组件的inputs必须是list")
        self._dependentComponent: List[BaseComponent] = inputs or []
        for c in self._dependentComponent:
            if not isinstance(c, BaseComponent):
                raise TypeError('inputs必须是BaseComponent类或子类')
        # 组件运行前传入的静态参数
        self._params = {}
        # 组件运行中产生的结果
        self._channel = {}
        for key, value in args.items():
            if type(value) == OutputChannel:  # 组件的Channels
                self._channel[key] = value
            else:  # 组件的params
                self._params[key] = value
        # 初始化Artifact
        self._artifact = Artifact()
        # 组件状态
        self._state = State()
        # 组件是否会共享
        self._datashared = shared
        # 找到依赖的组件后，就该将他们的channel、artifact加入进来，这个具体的由pipeline操作
        self._dependentChannels = {}
        self._dependentArtifacts = {}
        # 拿到executor class
        self._executor_cls = executor
        self._deploytype = None
        # 检查executor class是否只重写了一个函数
        # if (bool(self._executor_cls.Do==BaseExecutor.Do)==bool(self._executor_cls.Cycle==BaseExecutor.Cycle)):
        #     raise  SyntaxError('Do与Cycle必须有且只能有一个被重写')
        # 组件在拓扑DAG里面第几层
        self._topoLayerIndex = -1
        # 当前节点的上游节点与下游节点
        self._upstreamComponents = set()
        self._downstreamComponents = set()
        # cache机制，判断当前组件是否与之前的组件有所变动,默认改变了，需要删除之前的数据
        self._changed = True
        self._namespace = None

    @property
    def topoLayerIndex(self):
        return self._topoLayerIndex

    @topoLayerIndex.setter
    def topoLayerIndex(self, index: int):
        if index < 0:
            raise Exception("组件的topo Index必须不小于0")
        self._topoLayerIndex = index

    @property
    def inputs(self):
        return self._dependentComponent

    @property
    def resourceNamepace(self):
        return self._namespace

    @resourceNamepace.setter
    def resourceNamepace(self, namespace: str):
        self._namespace = namespace

    @property
    def outputs(self):
        return self._channel

    @property
    def dependentComponent(self):
        return self._dependentComponent

    @property
    def upstreamComponents(self):
        return self._upstreamComponents

    def add_upstream_Components(self, component):
        self._upstreamComponents.add(component)

    @property
    def changed(self):
        return self._changed

    def setChanged(self, changed: bool):
        self._changed = changed

    @property
    def downstreamComponents(self):
        return self._downstreamComponents

    def add_downstream_Components(self, component):
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

        可以由组件的构造函数的instance_name指定，或者由系统分配，组件的id在pipeline里唯一
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
        # if(self._executor_cls.Do!=BaseExecutor.Do):
        #     return 'Do'
        # else:
        #     return 'Cycle'
        return self._deploytype

    @deploytype.setter
    def deploytype(self, d_type):
        if d_type not in BaseComponentDeployType._value2member_map_:
            raise exception.DeployTypeError('DeployType只能是Do或者Cycle')
        self._deploytype = d_type

    @property
    def datashared(self) -> bool:
        '''组件的数据是否会共享出来
        '''
        return self._datashared

    @id.setter
    def id(self, _id: str):
        _id = _id or ''
        if not isinstance(_id, str):
            raise TypeError('组件id必须是str类型')
        if _id == '':  # 如果用户没有指定，就用类的名称做id
            #print('component id： ',self.__class__.__name__)
            self._id = str(self.__class__.__name__).lower()
        else:
            self._id = _id.lower()

    @classmethod
    def get_class_type(cls) -> str:
        return '.'.join([cls.__module__, cls.__name__])

    def to_json_dict(self):
        json_dict = {}
        for k, v in self.__dict__.items():
            if k not in [
                    '_downstreamComponents', '_upstreamComponents',
                    '_dependentComponent'
            ]:
                json_dict[k] = v
            elif k in ['_downstreamComponents', '_upstreamComponents']:
                json_dict[k] = [component.id for component in v]
        return json_dict

    @property
    def state(self) -> State:
        return self._state

    @state.setter
    def state(self, json2state: Dict[str, Any]) -> None:
        self._state = State(data=json2state)

    def static_check(self,task_name:str,model_name:str):
        """
        description
        ---------
        组件在被解析成workflow资源的之前的静态过程。

        比如model generator组件与model serving组件，就需要进行模型依赖DAG图的构建，在这个构建的过程里
        需要确保DAG不能出现环

        Args
        -------
        task_name:str pipeline的task名称

        model_name:str pipeline的model名称

        Returns
        -------
        
        Raises
        -------
        
        """
        raise Exception("must be extended")
    """
    todo:组件的缓存复用检测目前是放在静态编译阶段，然后将是否可复用的flag传递到组件里
    组件序列化后，编排器再执行的时候会根据这个flag判断是否要清空之前的数据。这样就会有一个问题，
    如果是cycle类型的组件，进程挂了后，再重启，会导致数据被删除，以后考虑将这个过程作为动态过程
    """
    def dynamic_check(self):
        """
        description
        ---------
        这个是当组件在实际被driver执行时的动态check过程
        Args
        -------
        
        Returns
        -------
        
        Raises
        -------
        
        """
        raise Exception("must be extended")
    
    def extra_svc_port_internal(self)->List[Tuple[str,str,int]]:
        """组件的运行需要暴露的端口
        有些时候，框架由于拓展性，组件可能需要自己运行一个server一类的程序，这个时候需要暴露端口出去，因此可以返回一个list：
        [("ts","TCP",8080),...],这里ts表示使用了torch serving框架
        """
        return []
    def extra_svc_port_user(self)->List[Tuple[str,str,int]]:
        """用户需要暴露的端口
        """
        return []
    def extra_pod_containers_internal(self)->List[PodContainer]:
        """框架需要的其他容器
        description
        ---------
        如果组件需要运行其他的服务，可以将其他的进程运行在其他的容器里。正常而言是不需要再运行
        其他服务，但举个例子，modelserving组件需要torchserving这么一个进程
        Args
        -------
        
        Returns
        -------
        
        Raises
        -------
        
        """
        return []
    def extra_pod_containers_user(self)->List[PodContainer]:
        """用户需要的容器
        """
        return []