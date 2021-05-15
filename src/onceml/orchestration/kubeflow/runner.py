import kfp
from onceml.orchestration.runner import BaseRunner
from onceml.orchestration import Pipeline
from onceml.components import BaseComponent
from kfp import compiler
from kfp import dsl
import os
import onceml.utils.json_utils as json_utils
import onceml.orchestration.kubeflow.kfp_component as Kfp_component

class KubeflowRunner(BaseRunner):
    def __init__(self, output_dir: str=None):

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

        Returns
        -------
        
        Raises
        -------
        
        """
        
        self._compiler = compiler.Compiler()
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
        #dsl_pipeline_root=
        print(file_name)
        self._compiler._create_and_write_workflow(
            pipeline_func=lambda:self._construct_pipeline_graph(pipeline),
            pipeline_name=pipeline.id,
            #params_list=self.kfp_parameters,
            package_path=os.path.join(self._output_dir,'yamls',file_name)
        )
