from typing import List
import kfp
from onceml.orchestration.runner import BaseRunner
from onceml.orchestration import Pipeline
from onceml.components.base import BaseComponent, GlobalComponent
from kfp import compiler
from kfp import dsl
import os
from onceml.utils import logger
import onceml.utils.json_utils as json_utils
import onceml.utils.pipeline_utils as pipeline_utils
import onceml.orchestration.kubeflow.kfp_component as Kfp_component
import onceml.orchestration.kubeflow.kfp_ops as kfp_ops
import onceml.utils.k8s_ops as k8s_ops
import onceml.orchestration.kubeflow.kfp_config as kfp_config
import onceml.types.exception as exception
import onceml.global_config as global_config


class KubeflowRunner(BaseRunner):
    def __init__(self,
                 output_dir: str = None,
                 kfp_host: str = None,
                 nfc_host: str = None,
                 docker_image: str = None,
                 namespace:str="kubeflow"):
        """负责将一个pipeline转换成kubeflow workflow资源
        description
        ---------
        workflow里的每一个组件会挂载output_dir目录，所以应当将output_dir设置为project根目录，
        会创建{output_dir}/yamls/、{output_dir}/outputs/两个目录

        {output_dir}/yamls/：存放pipeline转换出来的workflow yaml资源，命名为{pipeline task name}_{pipeline model name}.yaml

        {output_dir}/outputs/:为每个pipeline的运行数据，在这个目录下会按照{task}/{model}/{component}三级目录区分

        https://github.com/kubeflow/pipelines/blob/master/samples/core/output_a_directory/output_a_directory.py

        Args
        -------
        output_dir：workflow yaml存放的路径即kfp输出的目录

        kfp_host:kfp 的mlpipeline svc的ip地址,如果不指定，会自己使用kubernetes python sdk搜索

        nfc_host：NFC服务器的ip，默认为当前机器的ip

        docker_image:kfp里面的pod使用的镜像
        
        namespace:将pod部署在某个namespace里

        Returns
        -------

        Raises
        -------

        """

        self._compiler = compiler.Compiler()
        self._kfp_client = kfp.Client(kfp_host or k8s_ops.get_kfp_host(
            kfp_config.SVCNAME, namespace=kfp_config.NAMESPACE))
        self._parameters = {}
        self.kfp_parameters = []
        self._output_dir = output_dir or kfp_config.KFPOUTPUT
        self.docker_image = docker_image
        self.namespace=namespace
        os.makedirs(os.path.join(self._output_dir, 'yamls'), exist_ok=True)

        # 在kfp中创建onceml专属的pv
        # kfp_ops.ensure_pv(self._output_dir,nfc_host=nfc_host)
        # kfp_ops.ensure_pvc()
    def _parse_parameter_from_pipeline(self, pipeline: Pipeline):
        '''从pipeline中解析每个组件需要的参数
        '''
        for component in pipeline.components:
            self._parse_parameter_from_component(component)
        # print(self._parameters)

    def _parse_parameter_from_component(self, component: BaseComponent):
        '''具体地解析组件的参数
        '''
        serialized_component = json_utils.componentDumps(component)
        # print(serialized_component)
        self._parameters[component.id] = serialized_component
        # print(self._parameters)
        for key, value in self._parameters.items():
            self.kfp_parameters.append(dsl.PipelineParam(name=key,
                                                         value=value))

    def _construct_pipeline_graph(self, pipeline: Pipeline):
        """Constructs a Kubeflow Pipeline graph.
        Args:
        pipeline: The logical TFX pipeline to base the construction on.
        pipeline_root: dsl.PipelineParam representing the pipeline root."""
        component_to_kfp_op = {}
        # component_to_kfp_op['nfs']=Kfp_component.NFSContainerOp(pipeline.id)
        for component in pipeline.components:
            # ktp_component=
            component.resourceNamepace=self.namespace
            depends_on = {}
            Do_deploytype = []
            for upstreamComponent in component.upstreamComponents:
                if upstreamComponent.deploytype == "Do":
                    Do_deploytype.append(upstreamComponent.id)
                depends_on[upstreamComponent.id] = component_to_kfp_op[
                    upstreamComponent.id]
            kfp_component = Kfp_component.KfpComponent(
                task_name=pipeline._task_name,
                model_name=pipeline._model_name,
                pipeline_root=pipeline.rootdir,
                component=component,
                depends_on=depends_on,
                Do_deploytype=Do_deploytype,
                docker_image=self.docker_image)
            component_to_kfp_op[component.id] = kfp_component.container_op

    def allocate_component_artifact_url(self, pipeline: Pipeline):
        '''给pipeline每个组件分配artifact的存储目录
        '''
        for c in pipeline.components:
            if type(c) == GlobalComponent:
                # 如果是共享组件，则会建立软链接目录
                if not os.path.exists(
                        os.path.join(self._output_dir, pipeline._task_name,
                                     c._alias_model_name,
                                     c._alias_component_id)):
                    logger.logger.error('全局组件{}的目录不存在'.format(c.id))
                    raise exception.FileNotFoundError()
                os.symlink(src=os.path.join(os.getcwd(), self._output_dir,
                                            pipeline._task_name,
                                            c._alias_model_name,
                                            c._alias_component_id),
                           dst=os.path.join(os.getcwd(), self._output_dir,
                                            pipeline.rootdir, c.id))
                c.artifact.setUrl(os.path.join(pipeline.rootdir, c.id))
            else:
                if not os.path.exists(
                        os.path.join(self._output_dir, pipeline.rootdir,
                                     c.id)):
                    logger.logger.warning('组件{}的目录不存在,现在创建'.format(c.id))
                    os.makedirs(os.path.join(self._output_dir,
                                             pipeline.rootdir, c.id),
                                exist_ok=True)
                c.artifact.setUrl(os.path.join(pipeline.rootdir, c.id))

    def deploy(self, pipeline: Pipeline):
        '''将一个pipeline编译成kubeflow的yaml资源,并提交

        '''
        output_path = os.path.join(self._output_dir, pipeline.rootdir)
        os.makedirs(output_path, exist_ok=True)
        file_name = pipeline.id + '.yaml'
        # self._parse_parameter_from_pipeline(pipeline)
        #self.allocate_component_artifact_url(pipeline=pipeline)
        pipeline.db_store()
        # 在kfp中创建本项目专属的nfs server与nfs svc
        kfp_ops.ensure_nfs_server(NFS_NAME=kfp_config.NFS_NAME,
                                  labels={
                                      kfp_config.NFS_POD_LABEL_KEY:
                                      global_config.PROJECTDIRNAME
                                  })
        kfp_ops.ensure_nfs_svc(NFS_SVC_NAME=kfp_config.NFS_NAME,
                               selector={
                                   kfp_config.NFS_POD_LABEL_KEY:
                                   global_config.PROJECTDIRNAME
                               })
        # 编译成workflow资源
        self._compiler._create_and_write_workflow(
            pipeline_func=lambda: self._construct_pipeline_graph(pipeline),
            pipeline_name=pipeline.id,
            # params_list=self.kfp_parameters,
            package_path=os.path.join(self._output_dir, 'yamls', file_name))
        # 在kfp中创建onceml专属的experiment
        kfp_ops.ensure_experiment(self._kfp_client, kfp_config.EXPERIMENT)
        # 对数据库中的信息进行更新
        self.db_store(pipeline)
        # 在kfp中创建运行相应的pipeline，并且将其归属于kfp_config.EXPERIMENT中
        kfp_ops.ensure_pipeline(
            self._kfp_client, os.path.join(self._output_dir, 'yamls',
                                           file_name), pipeline)

    def db_store(self, pipeline: Pipeline):
        '''将kfp的信息存储
        '''
        pipeline_utils.change_pipeline_phase_to_created(pipeline.id)
        for c in pipeline.components:
            pipeline_utils.change_components_phase_to_created(
                pipeline_id=pipeline.id, component_id=c.id)
