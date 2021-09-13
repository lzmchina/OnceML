from onceml.orchestration.runner import BaseRunner
from onceml.orchestration import Pipeline
import onceml.utils.pipeline_utils as pipeline_utils
import os
import onceml.global_config as global_config


class OnceMLRunner(BaseRunner):
    def __init__(self,
                 pvc: str = None,
                 docker_image: str = None,
                 namespace: str = "onceml"):
        """负责将一个pipeline转换成OnceML workflow资源
        description
        ---------
        workflow里的每一个组件会挂载pvc

        {output_dir}/yamls/：存放pipeline转换出来的workflow yaml资源，命名为{pipeline task name}_{pipeline model name}.yaml

        {output_dir}/:为每个pipeline的运行数据，在这个目录下会按照{task}/{model}/{component}三级目录区分

        https://github.com/kubeflow/pipelines/blob/master/samples/core/output_a_directory/output_a_directory.py

        Args
        -------
        pvc:要挂载的pvc名称

        docker_image:kfp里面的pod使用的镜像
        
        namespace:将pod部署在某个namespace里

        Returns
        -------

        Raises
        -------

        """

        self._output_dir = os.path.join(global_config.PROJECTDIR,
                                        global_config.OUTPUTSDIR)
        self.docker_image = docker_image
        self.namespace = namespace
        os.makedirs(os.path.join(self._output_dir, 'yamls'), exist_ok=True)

    def _construct_pipeline_graph(self, pipeline: Pipeline):
        """Constructs a Kubeflow Pipeline graph.
        Args:
        pipeline: The logical TFX pipeline to base the construction on.
        pipeline_root: dsl.PipelineParam representing the pipeline root."""
        component_to_kfp_op = {}
        # component_to_kfp_op['nfs']=Kfp_component.NFSContainerOp(pipeline.id)
        for component in pipeline.components:
            # 分配namespace
            component.resourceNamepace = self.namespace
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

    def deploy(self, pipeline: Pipeline):
        '''将一个pipeline编译成kubeflow的yaml资源,并提交

        '''
        output_path = os.path.join(self._output_dir, pipeline.rootdir)
        os.makedirs(output_path, exist_ok=True)
        file_name = pipeline.id + '.yaml'

        pipeline.db_store()
        # 在kfp中创建本项目专属的nfs server与nfs svc

        # 编译成workflow资源

        # 对数据库中的信息进行更新
        self.db_store(pipeline)
        # 在kfp中创建运行相应的pipeline，并且将其归属于kfp_config.EXPERIMENT中

    def db_store(self, pipeline: Pipeline):
        '''将phase更新
        '''
        pipeline_utils.change_pipeline_phase_to_created(pipeline.id)
        for c in pipeline.components:
            pipeline_utils.change_components_phase_to_created(
                pipeline_id=pipeline.id, component_id=c.id)
