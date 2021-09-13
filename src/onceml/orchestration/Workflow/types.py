from typing import Any, Dict, List
from kubernetes.client.models import V1PodSpec, V1Container, V1Volume, V1beta1CustomResourceDefinition, V1ObjectMeta, V1beta1CustomResourceDefinitionSpec


class Containerop():
    def __init__(self):
        self.name = ''
        self.container: V1Container = V1Container()
        self.labels: Dict[str, Any] = {}
        self.volumes: List[V1Volume] = []

    def add_pod_label(self, name: str, value: str):
        '''给pod增加label
        '''
        self.labels.update(name, value)

    def add_volume(self, v: V1Volume):
        '''给pod增加volume
        '''
        self.volumes.append(v)


class Workflow(V1beta1CustomResourceDefinition):
    def __init__(self, name: str):
        self.api_version = ""
        self.kind = 'Workflow'
        self.metadata = V1ObjectMeta(name=name)
        self.spec:Dict[str,List] = {"templates": [], "dag": []}
    def add_component(self,c:Containerop):
        '''添加组件
        '''
        self.spec['templates'].append(c)
    def add_dag_layer(self,layer:List[Dict[str,str]]):
        '''添加一层dag
        '''
        self.spec['dag'].append(layer)