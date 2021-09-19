from os import name
from typing import Any, Dict, List
from kubernetes.client.models import V1PodSpec, V1Container, V1VolumeMount, V1ContainerPort, V1EnvVar, V1Volume, V1beta1CustomResourceDefinition, V1ObjectMeta, V1beta1CustomResourceDefinitionSpec
import six
import inspect


class Container():
    def __init__(self) -> None:
        self.args: list[str] = None
        self.command: list[str] = None
        self.env: list[V1EnvVar] = None
        self.image: str = None
        self.ports: list[V1ContainerPort] = None
        self.volumeMounts: list[V1VolumeMount] = None
        self.workingDir: str = None

    def to_dict(self):
        return self.__dict__


class Containerop():
    def __init__(self, name: str):
        self.name = name
        self.container: Container = Container()
        self.labels: Dict[str, Any] = {}
        self.volumes: List[V1Volume] = []

    def add_pod_label(self, name: str, value: str):
        '''给pod增加label
        '''
        self.labels.update({name: value})

    def add_volume(self, v: V1Volume):
        '''给pod增加volume
        '''
        self.volumes.append(v)

    def to_dict(self):
        return self.__dict__


class Workflow():
    _types = {
        'apiVersion': 'str',
        'kind': 'str',
        'metadata': 'V1ObjectMeta',
        'spec': 'V1beta1CustomResourceDefinitionSpec'
    }

    def __init__(self, name: str):
        self.apiVersion = ""
        self.kind = 'Workflow'
        self.metadata = V1ObjectMeta(name=name)
        self.spec: Dict[str, List] = {"templates": [], "dag": []}

    def add_component(self, c: Containerop):
        '''添加组件
        '''
        self.spec['templates'].append(c)

    def add_dag_layer(self, layer: List[Dict[str, str]]):
        '''添加一层dag
        '''
        self.spec['dag'].append(layer)

    def to_dict(self):
        """Returns the model properties as a dict"""

        return to_yaml(self.__dict__)


def to_yaml(obj):
    out = None
    if type(obj) == dict:
        out = {}
        for (var, value) in list(obj.items()):
            if value is not None:
                out[str(var)] = to_yaml(value)
    elif type(obj) == list:
        out = []
        for value in obj:
            out.append(to_yaml(value))
    elif hasattr(obj, "to_dict"):
        return to_yaml(obj.to_dict())
    #基本类型
    else:
        out = str(obj)
    return out