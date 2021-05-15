# -*- encoding: utf-8 -*-
'''
@Description	:pipline class

@Date	:2021/04/19 10:15:35

@Author	:lzm

@version	:0.0.1
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from typing import List, Optional, Text, Dict
from onceml.components import BaseComponent
from onceml.utils import topsorted_layers
import os

class Pipeline():
    '''将一个流水线抽象为pipline

    Pipline的逻辑：

    一个pipline可以看作是多个组件component的组成，比如从数据源、数据预处理、……最后到模型发布

    而且一个pipline要做到模型分离，对于同一个场景，使用的数据相同，而模型不同，所以需要做到模型的训练分离
    '''

    def __init__(self, task_name: str, model_name: str, components: Optional[Dict[str, BaseComponent]]):
        """
        description
        ---------
        一个基本的pipline class,会将task_name与model_name进行拼接，作为唯一标识符


        Args
        -------

        task_name (str):  
            给pipline所属的task命名

        model_name (str): 
            给这个pipline运行的model进行命名  

        components (List[BaseComponent]):
            这个pipline有哪些组件

        Returns
        -------
        None

        Raises
        ------
        TypeError:没有按照给定的参数类型来构造
        """
        # type check
        if not isinstance(task_name, str) or not isinstance(model_name, str):
            raise TypeError
        # _components为components经过拓扑结构处理后的结果，DAG(有向无环图)
        for key, v in components.items():
            v.id = key
        self.components = components.values() or []
        self.id = (task_name, model_name)

    @property
    def rootdir(self) -> str:
        '''pipine结果存放的目录*/{task name}/{model name}
        '''
        return self._rootdir
    @rootdir.setter
    def rootdir(self,tuple_name):
        task_name, model_name=tuple_name[0],tuple_name[1]
        if '/' in task_name or '/' in model_name:
            raise RuntimeError("pipline的task name:%s 或者 model name:%s不能包含 '/'符号 "%(task_name,model_name))
        self._rootdir=os.path.join(task_name,model_name)
    @property
    def id(self) -> str:

        return self._id

    @id.setter
    def id(self,tuple_name:tuple):
        '''pipline的唯一id，{task name}_{model name}
        '''
        task_name, model_name=tuple_name[0],tuple_name[1]
        if '_' in task_name or '_' in model_name:
            raise RuntimeError("pipline的task name:%s 或者 model name:%s不能包含 '_'符号 "%(task_name,model_name))
        self._id=task_name+'_'+model_name
        self.rootdir=tuple_name
    @property
    def components(self):
        """pipline的组件

        这些组件按照设置的逻辑拓扑排列
        """
        return self._components

    @property
    def layerComponents(self):
        """pipline的组件

        这些组件按照设置的逻辑拓扑排列,并且会分层
        """
        return self._layersComponents

    @components.setter
    def components(self, components: List[BaseComponent]):

        # 转化为set
        deduped_components = set(components)
        producer_map = {}
        node_ids = set()
        for component in deduped_components:
            #print('components.setter', component.id, component.type)
            if component.id in node_ids:
                raise RuntimeError('重复的id： %s ,其class type为%s' %
                                   (component.id, component.type))
            node_ids.add(component.id)

        for component in deduped_components:
            # 遍历组件的依赖组件
            for dependency_c in component.inputs:
                component.add_upstream_Components(dependency_c)  # 添加上游组件
                dependency_c.add_downstream_Components(component)  # 添加下游组件

        self._layersComponents = topsorted_layers(
            list(deduped_components),
            get_node_id_fn=lambda c: c.id,
            get_parent_nodes=lambda c: c.upstreamComponents,
            get_child_nodes=lambda c: c.downstreamComponents
        )
        self._components = []
        '''对component的deploytype进行检测，        
        Do:一次执行结束,后续组件可以是Cycle，也可以是Do
        Cycle：循环执行，后续组件只能是Cycle，因为需要靠发送http请求来驱动后续的组件执行一次

        所以这里进行一个判断
        '''
        for index, layer in enumerate(self._layersComponents):
            print('第 %d 层' % index)
            for component in layer:
                print('component id %s' % component.id)
                # 如果是Cycle类型的组件，就要检查他的直接后继节点是否是Cycle
                if component.deploytype == 'Cycle':
                    for downc in component.downstreamComponents:
                        if downc.deploytype != 'Cycle':
                            raise RuntimeError('Cycle 类型的组件： %s ,后继组件出现了Do类型' %
                                               (component.id))
                self._components.append(component)

    def _testrun(self):
        for c in self._components:
            c.execute()
            print('dependency:', c.upstreamComponents, c.downstreamComponents)
