import kfp
from kubernetes.config import kube_config
from onceml.orchestration.runner import BaseRunner
from onceml.orchestration import Pipeline
from onceml.components import BaseComponent
from kfp import compiler
from kfp import dsl
import os
import onceml.utils.json_utils as json_utils
import onceml.orchestration.kubeflow.kfp_component as Kfp_component
import onceml.orchestration.kubeflow.kfp_ops as kfp_ops
import onceml.utils.k8s_ops as k8s_ops
import onceml.orchestration.kubeflow.kfp_config as kfp_config
class KubeflowRunner(BaseRunner):
    def __init__(self, output_dir: str=None,kfp_host:str=None):

        """负责将一个pipline转换成kubeflow workflow资源
        description
        ---------
        workflow里的每一个组件会挂载output_dir目录，所以应当将output_dir设置为project根目录，
        会创建{output_dir}/yamls/、{output_dir}/outputs/两个目录

        {output_dir}/yamls/：存放pipline转换出来的workflow yaml资源，命名为{pipline task name}_{pipline model name}.yaml

        {output_dir}/outputs/:为每个pipline的运行数据，在这个目录下会按照{task}/{model}/{component}三级目录区分

        https://github.com/kubeflow/pipelines/blob/master/samples/core/output_a_directory/output_a_directory.py
        
        Args
        -------
        output_dir：workflow yaml存放的路径

        kfp_host:kfp 的mlpipline svc的ip地址,如果不指定，会自己使用kubernetes python sdk搜索

        Returns
        -------
        
        Raises
        -------
        
        """
        
        self._compiler = compiler.Compiler()
        kfp_host=kfp_host or k8s_ops.get_kfp_host(kfp_config.SVCNAME,namespace=kfp_config.NAMESPACE)
        self._kfp_client=kfp.Client(kfp_host)
        self._parameters = {}
        self.kfp_parameters = []
        self._output_dir = output_dir or os.getcwd()
        os.makedirs(os.path.join(self._output_dir,'yamls'),exist_ok=True)
    def _parse_parameter_from_pipeline(self, pipline: Pipeline):
        '''从pipline中解析每个组件需要的参数
        '''
        for component in pipline.components:
            self._parse_parameter_from_component(component)
        #print(self._parameters)

    def _parse_parameter_from_component(self, component: BaseComponent):
        '''具体地解析组件的参数
        '''
        serialized_component = json_utils.componentDumps(component)
        # print(serialized_component)
        self._parameters[component.id] = serialized_component
        # print(self._parameters)
        for key, value in self._parameters.items():
            self.kfp_parameters.append(dsl.PipelineParam(name=key, value=value))
    def _construct_pipeline_graph(self, pipeline: Pipeline):
        """Constructs a Kubeflow Pipeline graph.
        Args:
        pipeline: The logical TFX pipeline to base the construction on.
        pipeline_root: dsl.PipelineParam representing the pipeline root."""
        component_to_kfp_op = {}
        for component in pipeline.components:
            #ktp_component=
            depends_on={}
            Do_deploytype=[]
            for upstreamComponent in component.upstreamComponents:
                if upstreamComponent.deploytype=="Do":
                    Do_deploytype.append(upstreamComponent.id)
                depends_on[upstreamComponent.id]=component_to_kfp_op[upstreamComponent.id]
            kfp_component=Kfp_component.KfpComponent(pipline_root=pipeline.rootdir,component=component,depends_on=depends_on,Do_deploytype=Do_deploytype)
            component_to_kfp_op[component.id]=kfp_component.container_op
    def deploy(self, pipeline: Pipeline):
        '''将一个pipline编译成kubeflow的yaml资源

        '''

        self._parse_parameter_from_pipeline(pipeline)
        output_path=os.path.join(self._output_dir,pipeline.rootdir)
        os.makedirs(output_path,exist_ok=True)
        file_name = pipeline.id+'.yaml'
        self._compiler._create_and_write_workflow(
            pipeline_func=lambda:self._construct_pipeline_graph(pipeline),
            pipeline_name=pipeline.id,
            #params_list=self.kfp_parameters,
            package_path=os.path.join(self._output_dir,'yamls',file_name)
        )
        #在kfp中创建onceml专属的experiment
        kfp_ops.ensure_experiment(self._kfp_client,kfp_config.EXPERIMENT)
        #在kfp中创建运行相应的pipline，并且将其归属于kfp_config.EXPERIMENT中
        kfp_ops.ensure_pipline(self._kfp_client,os.path.join(self._output_dir,'yamls',file_name),pipeline.id)
