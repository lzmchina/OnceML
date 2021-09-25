from collections import OrderedDict
from typing import Dict
from onceml.orchestration.runner import BaseRunner
from onceml.orchestration import Pipeline
import onceml.utils.pipeline_utils as pipeline_utils
import os
import onceml.global_config as global_config
from onceml.orchestration.Workflow.component import OnceMLComponent
from onceml.orchestration.Workflow.types import Workflow
from onceml.components.base import BaseComponent
import yaml
import kubernetes.utils as k8s_utils


class OnceMLRunner(BaseRunner):
    def __init__(self,
                 pvc: str,
                 project_name: str,
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
        self.pvcname = pvc
        self.project_name = project_name
        os.makedirs(os.path.join(self._output_dir, 'yamls'), exist_ok=True)

    def construct_pipeline_graph(
            self, pipeline: Pipeline) -> Dict[str, OnceMLComponent]:
        """
        """
        component_to_kfp_op = {}
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
            workflow_component = OnceMLComponent(
                task_name=pipeline._task_name,
                model_name=pipeline._model_name,
                component=component,
                Do_deploytype=Do_deploytype,
                pvc_name=self.pvcname,
                project_name=self.project_name)
            component_to_kfp_op[component.id] = workflow_component
        return component_to_kfp_op

    def deploy(self, pipeline: Pipeline):
        '''将一个pipeline编译成workfow的yaml资源,并提交(optional)

        '''
        output_path = os.path.join(self._output_dir, pipeline.rootdir)
        os.makedirs(output_path, exist_ok=True)
        file_name = pipeline.id + '.test.yaml'

        pipeline.db_store()
        # 编译成workflow资源
        workflow = Workflow("{project}.{}".format(pipeline.id,
                                                  project=self.project_name))
        for c in self.construct_pipeline_graph(pipeline=pipeline).values():
            workflow.add_component(c.containerop)
        for layer in pipeline.layerComponents:
            dag_layer = []
            for component in layer:
                dag_layer.append({
                    "name": component.id,
                    "deployType": component.deploytype
                })
            workflow.add_dag_layer(dag_layer)

        print(
            yaml.dump(
                workflow.to_dict(),
                open(os.path.join(self._output_dir, 'yamls', file_name), "w")))
        # 对数据库中的信息进行更新
        #self.db_store(pipeline)

    def db_store(self, pipeline: Pipeline):
        '''将phase更新
        '''
        pipeline_utils.change_pipeline_phase_to_created(pipeline.id)
        for c in pipeline.components:
            pipeline_utils.change_components_phase_to_created(
                pipeline_id=pipeline.id, component_id=c.id)


def dump_yaml(data):
    #See https://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts/21912744#21912744

    def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
        class OrderedDumper(Dumper):
            pass

        def _dict_representer(dumper, data):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

        OrderedDumper.add_representer(OrderedDict, _dict_representer)
        OrderedDumper.add_representer(dict, _dict_representer)

        #Hack to force the code (multi-line string) to be output using the '|' style.
        def represent_str_or_text(self, data):
            style = None
            if data.find('\n') >= 0:  #Multiple lines
                #print('Switching style for multiline text:' + data)
                style = '|'
            if data.lower() in [
                    'y', 'n', 'yes', 'no', 'true', 'false', 'on', 'off'
            ]:
                style = '"'
            return self.represent_scalar(u'tag:yaml.org,2002:str', data, style)

        OrderedDumper.add_representer(str, represent_str_or_text)

        return yaml.dump(data, stream, OrderedDumper, **kwds)

    return ordered_dump(data, default_flow_style=None)