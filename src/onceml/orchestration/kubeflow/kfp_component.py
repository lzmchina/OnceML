from kfp import dsl
from typing import Set,Dict,List

import onceml.components.base.base_component as base_component
import onceml.utils.json_utils as json_utils
import onceml.orchestration.kubeflow.kfp_config as kfp_config
import onceml.types.channel as channel
import onceml.types.artifact as artifact
class KfpComponent:
    '''kubeflow workflow中的一个组件

    将pipline的组件转化至kfpComponent，包含执行的命令、使用的镜像、挂载的pv等信息
    '''

    def __init__(self, pipline_root:str,component: base_component.BaseComponent, depends_on: Dict[str,dsl.ContainerOp],Do_deploytype:List[str]):
        """kubeflow component的表示
        description
        ---------
        kubeflow需要组件返回dsl.ContainerOp，这个类就是包装，同时还有其他信息，最终返回一个dsl.ContainerOp

        Args
        -------
        pipline_root:组件所属pipline的根目录，通常为{task name}/{model name}

        component：本pipline的component

        depends_on： component依赖的其他 component的ContainerOp

        1. 如果是Do类型的组件，则需要添加依赖after，并且获得其输出，并将输出给到组件

        2. 如果是Cycle类型的组件，则需要考虑他的上游节点中的Do类型的组件，并获得其输出，同时对上游节点中的Cycle类型的组件，使用相应的init容器进行延迟创建
        Returns
        -------

        Raises
        -------

        """
        arguments = [
            '--component_id',
            component.id,
            '--serialized_component',
            json_utils.componentDumps(component)
        ]

        if component.deploytype == 'Do':
            d_channels={}#获取依赖的Do类型的组件的channel输出路径
            d_artifact={}#获取依赖的Do类型的组件的artifact输出路径
            for c_id,v in depends_on.items():
                d_channels[c_id]=v.outputs['channels']
                d_artifact[c_id]=v.outputs['artifact']
            arguments=arguments+[
                '--d_channels',
                d_channels,
                '--d_artifact',
                d_artifact

            ]
            self.container_op = dsl.ContainerOp(
                name=component.id.replace('.', '_'),
                command=kfp_config.COMMAND,
                image=kfp_config.IMAGE,
                arguments=arguments,
                file_outputs={#存放组件的channels结果的文件，方便ui可视化
                    'mlpipeline-ui-metadata':'%s/%s/result.json'%(pipline_root,component.id),
                    'channels':'%s/%s/result.json'%(pipline_root,component.id),
                    'artifact':'%s/%s/artifact'%(pipline_root,component.id)
                }
            )
            for c_id,v in depends_on.items():
                self.container_op.after(v)
        else:
            d_channels={}#获取依赖的Do类型的组件的channel输出路径
            d_artifact={}#获取依赖的Do类型的组件的artifact输出路径
            for c_id,v in depends_on.items():
                d_channels[c_id]=v.outputs['channels']
                d_artifact[c_id]=v.outputs['artifact']
            arguments=arguments+[
                '--d_channels',
                d_channels,
                '--d_artifact',
                d_artifact

            ]
            self.container_op = dsl.ContainerOp(
                name=component.id.replace('.', '_'),
                command=kfp_config.COMMAND,
                image=kfp_config.IMAGE,
                arguments=arguments,
                file_outputs={#存放组件的channels结果的文件，方便ui可视化
                    'mlpipeline-ui-metadata':'%s/%s'%(pipline_root,component.id),
                    'channels':'%s/%s/result.json'%(pipline_root,component.id),
                    'artifact':'%s/%s/artifact'%(pipline_root,component.id)
                },
                container_kwargs={

                }
            )
            for c_id,v in depends_on.items():
                if c_id in Do_deploytype:
                    self.container_op.after(v)
            #设置一个init container，用来检查依赖的Cycle类型的组件server是否已经完成
            self.container_op.add_init_container(dsl.UserContainer(
                name='check dependency',
                image='',
            ))
        #取消kfp自带的cache机制
        self.container_op.execution_options.caching_strategy.max_cache_staleness = "P0D"
        #给pod添加label，方便后续的查询
        self.container_op.add_pod_label(name='onceml',value=('%s_%s'%(pipline_root,component.id)).replace('/','_'))