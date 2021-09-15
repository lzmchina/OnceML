# -*- encoding: utf-8 -*-
'''
@Description	:pipeline class

@Date	:2021/04/19 10:15:35

@Author	:lzm

@version	:0.0.1
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from typing import List, Optional, Text, Dict
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.utils.topsort import topsorted_layers
import os
import onceml.types.exception as exception
import onceml.utils.pipeline_utils as pipeline_utils
from onceml.utils.json_utils import Jsonable
from onceml.components.base.global_component import GlobalComponent
from onceml.utils.logger import logger
import onceml.global_config as global_config


# class PipelineParam(Jsonable):
#     def
#     def to_json_dict(self):
#         return super().to_json_dict()
class Pipeline():
    '''将一个流水线抽象为pipeline

    Pipeline的逻辑：

    一个pipeline可以看作是多个组件component的组成，比如从数据源、数据预处理、……最后到模型发布

    而且一个pipeline要做到模型分离，对于同一个场景，使用的数据相同，而模型不同，所以需要做到模型的训练分离
    '''
    def __init__(self, task_name: str, model_name: str,
                 components: Optional[Dict[str, BaseComponent]]):
        """
        description
        ---------
        一个基本的pipeline class,会将task_name与model_name进行拼接，作为唯一标识符
        同时会与depend_model联系起来


        Args
        -------

        task_name (str):  
            给pipeline所属的task命名

        model_name (str): 
            给这个pipeline运行的model进行命名  

        components (List[BaseComponent]):
            这个pipeline有哪些组件

        depend_model:
            依赖的模型集合，针对的是同一task

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

        self._task_name = task_name.lower()
        self._model_name = model_name.lower()
        self.id = (task_name, model_name)
        self.components = components.values() or []
        self.allocate_component_artifact_url()
        # 依赖的模型
        #self._depend_models = []
        #self.depend_models = depend_models

    # @property
    # def depend_models(self):
    #     '''获取依赖的model，即依赖哪些pipeline
    #     '''
    #     return self._depend_models

    # @depend_models.setter
    # def depend_models(self, model_list: list):
    #     '''设置依赖的pipeline
    #     '''
    #     self._depend_models = []
    #     for model in model_list:
    #         if not pipeline_utils.db_check_pipeline('_'.join([self._task_name,model])):
    #             #说明依赖的model不存在
    #             raise exception.PipelineNotFoundError('{}并不存在'.format('_'.join([self._task_name,model])))
    #         self._depend_models.append(self._task_name+'_'+model)

    @property
    def rootdir(self) -> str:
        '''pipine结果存放的目录*/{task name}/{model name}
        '''
        return self._rootdir

    @rootdir.setter
    def rootdir(self, tuple_name):
        task_name, model_name = tuple_name[0], tuple_name[1]
        if '/' in task_name or '/' in model_name:
            raise RuntimeError(
                "pipeline的task name:%s 或者 model name:%s不能包含 '/'符号 " %
                (task_name, model_name))
        self._rootdir = os.path.join(task_name.lower(), model_name.lower())

    @property
    def id(self) -> str:

        return self._id

    @id.setter
    def id(self, tuple_name: tuple):
        '''pipeline的唯一id，{task name}_{model name}
        '''
        chars = set('-_/')
        task_name, model_name = tuple_name[0], tuple_name[1]
        if any((c in chars) for c in task_name) or any(
            (c in chars) for c in model_name):
            raise RuntimeError(
                "pipeline的task name:%s 或者 model name:%s不能包含 '{}'符号 " %
                (task_name, model_name, chars))
        self._id = (str(task_name + '.' + model_name)).lower()
        self.rootdir = tuple_name

    @property
    def components(self) -> List[BaseComponent]:
        """pipeline的组件

        这些组件按照设置的逻辑拓扑排列
        """
        return self._components

    @property
    def layerComponents(self) -> List[List[BaseComponent]]:
        """pipeline的组件

        这些组件按照设置的逻辑拓扑排列,并且会分层
        """
        return self._layersComponents

    @components.setter
    def components(self, components: List[BaseComponent]):

        # 转化为set
        deduped_components = set(components)
        node_ids = set()
        for component in deduped_components:
            #print('components.setter', component.id, component.type)
            if component.id in node_ids:
                raise RuntimeError('重复的id： %s ,其class type为%s' %
                                   (component.id, component.type))
            node_ids.add(component.id)
            # 对component的deploytype继续填充，因为组件没有这一步骤，GlobalComponent类型的组件需要找到他的别名组件
            self.fill_c_deploytype_field(component)
            # 遍历组件的依赖组件
            for dependency_c in component.inputs:
                component.add_upstream_Components(dependency_c)  # 添加上游组件
                dependency_c.add_downstream_Components(component)  # 添加下游组件

        self._layersComponents = topsorted_layers(
            list(deduped_components),
            get_node_id_fn=lambda c: c.id,
            get_parent_nodes=lambda c: c.upstreamComponents,
            get_child_nodes=lambda c: c.downstreamComponents)
        self._components = []
        '''对component的deploytype进行检测，        
        Do:一次执行结束,后续组件可以是Cycle，也可以是Do
        Cycle：循环执行，后续组件只能是Cycle，因为需要靠发送http请求来驱动后续的组件执行一次

        所以这里进行一个判断
        '''
        for index, layer in enumerate(self.layerComponents):
            logger.info('第 %d 层' % index)
            for component in layer:
                logger.info('component id %s' % component.id)

                # 同时利用cache机制，判断是否可以利用之前的数据
                pipeline_utils.compare_component(self._task_name,
                                                 self._model_name, component)
                if component.deploytype is None:
                    raise exception.DeployTypeError(
                        'component {}必须有一种deploytype'.format(component.id))

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
            logger.info('dependency:', c.upstreamComponents,
                        c.downstreamComponents)

    def custom_static_check(self):
        '''在deploy开始前检查pipeline,通常为组件的自检
        '''
        pass

    def fill_c_deploytype_field(self, component: BaseComponent):
        if type(component) == GlobalComponent:
            logger.info('pipeline: {} 的component :{}为全局组件，别名{}中{}组件'.format(
                self.id, component.id, component.alias_model_name,
                component.alias_component_id))
            assert component.id == component.alias_component_id, "为避免后续组件接收id重复问题，global component的id要与alias一致"
            # GlobalComponent不应具有上游组件
            if len(component.dependentComponent) > 0:
                logger.error('GlobalComponent 不应具有上游组件')
                raise RuntimeError()
            if not pipeline_utils.db_check_pipeline(
                    self._task_name.lower(),
                    component.alias_model_name.lower()):
                # 检查同一task下的model是否存在
                logger.error('pipeline id :{}不存在 '.format(
                    pipeline_utils.generate_pipeline_id(
                        task_name=self._task_name.lower(),
                        model_name=component.alias_model_name.lower())))
                raise exception.PipelineNotFoundError()
            if not pipeline_utils.db_check_pipeline_component(
                    self._task_name.lower(),
                    component.alias_model_name.lower(),
                    component.alias_component_id):
                # 再检查别名的组件是否存在
                logger.error('pipeline id :{}不存在 组件：{}'.format(
                    '_'.join([self._task_name, component.alias_model_name]),
                    component.alias_component_id))
                raise exception.ComponentNotFoundError()
            # 然后再根据别名组件,得到他的deploytype
            component.deploytype = pipeline_utils.db_get_pipeline_component_deploytype(
                self._task_name, component.alias_model_name,
                component.alias_component_id)
            # 更新一下alias的组件，可能存在较长alias链，这时需要找到最初的那个
            origin_model, origin_component = pipeline_utils.recursive_get_global_component_alias_component(
                self._task_name, component.alias_model_name,
                component.alias_component_id)
            component.alias_component_id = origin_component
            component.alias_model_name = origin_model
            #component.deploytype='Cycle'
        else:
            # 说明是普通的组件，直接通过executor class的信息判断
            if (bool(component._executor_cls.Do == BaseExecutor.Do) == bool(
                    component._executor_cls.Cycle == BaseExecutor.Cycle)):
                raise SyntaxError('Do与Cycle必须有且只能有一个被重写')
            if (component._executor_cls.Do != BaseExecutor.Do):
                component.deploytype = 'Do'
            else:
                component.deploytype = 'Cycle'

    def allocate_component_artifact_url(self):
        '''给pipeline每个组件分配artifact的存储目录
        '''
        for c in self.components:
            if type(c) == GlobalComponent:
                #如果是共享组件，他的目录就应该是alias组件的目录
                c.artifact.setUrl(
                    os.path.join(self._task_name, c.alias_model_name,
                                 c.alias_component_id))
            else:

                c.artifact.setUrl(os.path.join(self.rootdir, c.id))

    def db_store(self):
        '''将数据保存到db里

        先保存组件，再保存pipeline
        因为是先查询pipeline，所以保存得反着来
        '''
        for component in self.components:
            if not pipeline_utils.db_update_pipeline_component(
                    task_name=self._task_name,
                    model_name=self._model_name,
                    component=component):
                logger.error('数据库更新pipeline id:{}下的组件: {}失败'.format(
                    self.id, component.id))
                raise exception.DBOpTypeError('数据库操作失败')
        if not pipeline_utils.db_update_pipeline(self._task_name,
                                                 self._model_name):
            logger.error('数据库更新pipeline id:{}失败'.format(self.id))
            raise exception.DBOpTypeError('数据库操作失败')

    def db_delete(self):
        '''将db里的数据删除

        先删除pipeline，再删除组件
        因为是先查询pipeline，所以保存得反着来
        '''
        if not pipeline_utils.db_delete_pipeline(self._task_name,
                                                 self._model_name):
            logger.error('数据库删除pipeline id:{}失败'.format(self.id))
            raise exception.DBOpTypeError('数据库操作失败')
        for component in self.components:
            if not pipeline_utils.db_delete_pipeline_component(
                    task_name=self._task_name,
                    model_name=self._model_name,
                    component=component):
                logger.error('数据库更新pipeline id:{}下的组件: {}失败'.format(
                    self.id, component.id))
                raise exception.DBOpTypeError('数据库操作失败')
