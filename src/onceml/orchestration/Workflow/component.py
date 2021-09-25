from typing import Dict, List
from kubernetes.client.models import V1VolumeMount, V1ContainerPort, V1Volume, V1EnvVar, V1PersistentVolumeClaimVolumeSource
import onceml.components.base.base_component as base_component
import onceml.utils.pipeline_utils as pipeline_utils
from onceml.orchestration.Workflow.types import Containerop
import onceml.orchestration.Workflow.config as podconfigs
import onceml.components.base.global_component as global_component
import onceml.configs.k8sConfig as k8sConfig
import onceml.global_config as global_config


class OnceMLComponent:
    '''onceml workflow中的一个组件

    将pipeline的组件转化至OnceMLComponent，包含执行的命令、使用的镜像、挂载的pv等信息
    '''
    def __init__(self,
                 task_name: str,
                 model_name: str,
                 component: base_component.BaseComponent,
                 Do_deploytype: List[str],
                 pvc_name: str,
                 docker_image: str = None,
                 project_name: str = None):
        """onceml component的表示
        description
        ---------
        将组件的运行信息转换成pod信息

        Args
        -------
      

        component：本pipeline的component

        depends_on： component依赖的其他 component的Containerop

        Do_deploytype:依赖的组件里，Do类型的有哪些



        Returns
        -------

        Raises
        -------

        """
        arguments = pipeline_utils.parse_component_to_container_entrypoint(
            component,
            task_name,
            model_name,
            Do_deploytype,
            project_name=project_name)
        self.containerop = Containerop(component.id)
        self.containerop.container.command = podconfigs.COMMAND
        self.containerop.container.args = arguments
        self.containerop.container.image = docker_image or podconfigs.IMAGE
        self.containerop.container.workingDir = podconfigs.WORKINGDIR
        self.containerop.container.volumeMounts = [
            V1VolumeMount(name=pvc_name, mount_path=podconfigs.WORKINGDIR)
        ]
        if component.deploytype == 'Cycle':
            #如果是Cycle，且不是global组件，则需要增加port配置
            #因为global组件相当于他别名的组件的替身，可以看作是他别名的组件要向后继组件发送消息
            if type(component) != global_component.GlobalComponent:
                self.containerop.container.ports = [
                    V1ContainerPort(
                        container_port=podconfigs.SERVERPORT)  # 开放端口
                ]
            # 设置pod的label，保证Cycle类型的组件能够打上上游cycle组件的标签，这样上游组件就可以通过label来获取要发送
            # 的组件的list
            for c in component.upstreamComponents:
                _model_name, _com_id = model_name, c.id
                # 如果是全局组件，并且是Cycle类型的，就要打上全局组件别名的组件的标签
                # 在前面pipeline给组件分配deploytype时，会更新global依赖的最原始的实际运行的组件
                if c.deploytype == 'Cycle':
                    if type(c) == global_component.GlobalComponent:
                        _model_name, _com_id = pipeline_utils.get_global_component_alias_component(
                            task_name=task_name,
                            model_name=model_name,
                            component=c)
                    self.containerop.add_pod_label(
                        name=k8sConfig.COMPONENT_SENDER_POD_LABEL.format(
                            project=project_name
                            or global_config.PROJECTDIRNAME,
                            task=task_name,
                            model=_model_name,
                            component=_com_id),
                        value=k8sConfig.COMPONENT_SENDER_POD_VALUE)
        # 进行nfs的volume挂载
        self.containerop.add_volume(
            V1Volume(
                name=pvc_name,
                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                    claim_name=pvc_name)))
        # 给pod添加label，方便后续的查询,value为{task name}_{model name}_{component id}
        self.containerop.add_pod_label(
            name=k8sConfig.COMPONENT_POD_LABEL,
            value=k8sConfig.COMPONENT_POD_LABEL_VALUE.format(
                project_name or global_config.PROJECTDIRNAME, task_name,
                model_name, component.id))
        #加入环境变量，方便pod里的程序能够使用api
        self.containerop.container.env = [
            V1EnvVar(name='{}ENV'.format(global_config.project_name),
                     value='INPOD')
        ]
