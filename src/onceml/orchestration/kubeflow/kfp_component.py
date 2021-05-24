from kfp import dsl
from typing import Set, Dict, List
from kubernetes.client.models import V1ContainerPort
import onceml.components.base.base_component as base_component
import onceml.components.base.global_component as global_component
import onceml.utils.json_utils as json_utils
import onceml.orchestration.kubeflow.kfp_config as kfp_config
import onceml.orchestration.kubeflow.kfp_ops as kfp_ops
import onceml.types.channel as channel
import onceml.types.artifact as artifact
import json
import onceml.utils.k8s_ops as k8s_ops
import onceml.global_config as global_config
import os


def NFSContainerOp(pipeline_id: str):
    '''运行NFS的容器
    '''
    nfsop = dsl.ResourceOp(
        name='mount-nfs',
        k8s_resource=json.loads(
            kfp_config.NFS_POD_TEMPLATE.format(
                nodeSelector=json.dumps(
                    {"kubernetes.io/hostname": k8s_ops.get_current_node_name()}).lower(),
                NFS_IMAGE=json.dumps(kfp_config.NFS_IMAGE),
                NFS_DIR=json.dumps(kfp_config.NFS_DIR),
                PROJECT_DIR=json.dumps(global_config.PROJECTDIR),
                NFS_NAME=json.dumps(global_config.PROJECTDIRNAME +
                                    '.'+pipeline_id.replace('_', '.').lower()),
                labels=json.dumps({
                    kfp_config.NFS_POD_LABEL_KEY: pipeline_id
                })
            )
        ),
        action='create'
    )

    return nfsop


class KfpComponent:
    '''kubeflow workflow中的一个组件

    将pipeline的组件转化至kfpComponent，包含执行的命令、使用的镜像、挂载的pv等信息
    '''

    def __init__(self, task_name: str, model_name: str, pipeline_root: str, component: base_component.BaseComponent, depends_on: Dict[str, dsl.ContainerOp], Do_deploytype: List[str]):
        """kubeflow component的表示
        description
        ---------
        kubeflow需要组件返回dsl.ContainerOp，这个类就是包装，同时还有其他信息，最终返回一个dsl.ContainerOp

        Args
        -------
        pipeline_root:组件所属pipeline的根目录，通常为{task name}/{model name}

        component：本pipeline的component

        depends_on： component依赖的其他 component的ContainerOp

        Do_deploytype:依赖的组件里，Do类型的有哪些

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
        d_channels = {}  # 获取依赖的Do类型的组件的channel输出路径
        d_artifact = {}  # 获取依赖的组件的artifact输出路径
        for c in component.upstreamComponents:
            if c.id in Do_deploytype:
                d_channels[c.id] = depends_on[c.id].outputs
            d_artifact[c.id] = c.artifact.url
        arguments = arguments+[
            '--d_channels',
            d_channels,
            '--d_artifact',
            d_artifact
        ]
        if component.deploytype == 'Do':

            self.container_op = dsl.ContainerOp(
                name=component.id.replace('.', '_'),
                command=kfp_config.COMMAND,
                image=kfp_config.IMAGE,
                arguments=arguments,
                file_outputs={  # 存放组件的channels结果的文件，方便ui可视化
                    'mlpipeline-ui-metadata': os.path.join(component.artifact.url, 'result.json'),
                    'channels': os.path.join(component.artifact.url, 'result.json'),
                    'artifact': os.path.join(component.artifact.url, 'artifact')
                },
                container_kwargs={
                    'working_dir': kfp_config.WORKINGDIR,
                    'volume_mounts': [
                        k8s_ops.client.V1VolumeMount(
                            name="nfs-volume",
                            mount_path=kfp_config.WORKINGDIR)
                    ]
                }
            )

        else:
            self.container_op = dsl.ContainerOp(
                name=component.id.replace('.', '_'),
                command=kfp_config.COMMAND,
                image=kfp_config.IMAGE,
                arguments=arguments,
                file_outputs={  # 存放组件的channels结果的文件，方便ui可视化
                    'mlpipeline-ui-metadata': os.path.join(component.artifact.url, 'result.json'),
                    'channels': os.path.join(component.artifact.url, 'result.json'),
                    'artifact': os.path.join(component.artifact.url, 'artifact')
                },
                container_kwargs={
                    'working_dir': kfp_config.WORKINGDIR,
                    'ports': [
                        V1ContainerPort(container_port=kfp_config.SERVERPORT)  # 开放端口
                    ],
                    'volume_mounts': [
                        k8s_ops.client.V1VolumeMount(
                            name="nfs-volume",
                            mount_path=kfp_config.WORKINGDIR)
                    ]
                }
            )
            # 设置一个init container，用来检查依赖的Cycle类型的组件server是否已经完成
            # self.container_op.add_init_container(dsl.UserContainer(
            #     name='check dependency',
            #     image='',
            # ))
            # 设置pod的label，保证Cycle类型的组件能够知道自己要向谁报告通信
            for c in component.upstreamComponents:
                _model_name, _com_id = model_name, c.id
                # 如果是全局组件，并且是Cycle类型的，就要打上全局组件别名的组件的标签
                if type(c) == global_component.GlobalComponent and c.deploytype == 'Cycle':
                    _model_name, _com_id = kfp_ops.get_global_component_alias_component(
                        task_name=task_name, model_name=model_name, component=c)
                self.container_op.add_pod_label(
                    name=kfp_config.COMPONENT_SENDER_POD_LABEL.format(
                        task=task_name,
                        model_name=_model_name,
                        component=_com_id
                    ),
                    value='1')
        # 设置本组件要在Do类型组件完成之后启动
        for c_id, v in depends_on.items():
            if c_id in Do_deploytype:
                self.container_op.after(v)
        # 进行nfs的volume挂载色临风
        self.container_op.add_volume(k8s_ops.client.V1Volume(
            name='nfs-volume',
            nfs=k8s_ops.client.V1NFSVolumeSource(
                server=k8s_ops.get_nfs_svc_ip(
                    NFS_SVC_NAME=kfp_config.NFS_SVC_NAME,
                    namespace=kfp_config.NAMESPACE
                ),
                path='/'
            )
        ))
        # self.container_op._container.add_volume_mount()
        # 取消kfp自带的cache机制
        self.container_op.execution_options.caching_strategy.max_cache_staleness = "P0D"
        # 给pod添加label，方便后续的查询,value为{task name}_{model name}_{component id}
        self.container_op.add_pod_label(name=kfp_config.COMPONENT_POD_LABEL, value=(
            '%s-%s-%s-%s' % (global_config.PROJECTDIRNAME, task_name, model_name, component.id)))
