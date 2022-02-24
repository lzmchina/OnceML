from os import name
from typing import Any, Dict, List, Tuple
from kubernetes.client.models import V1PodSpec, V1Container, V1VolumeMount, V1PersistentVolumeClaimVolumeSource, V1ContainerPort, V1EnvVar, V1Volume, V1beta1CustomResourceDefinition, V1ObjectMeta, V1beta1CustomResourceDefinitionSpec
import six
import inspect


def check_containers(tochecks) -> bool:
    if not isinstance(tochecks, list):
        return False
    if not all([isinstance(x, PodContainer) for x in tochecks]):
        return False
    return True


def check_svc(tochecks) -> bool:
    """检查svc的声明规则
    list： [("ts","TCP",8080),...],这里ts表示使用了torch serving框架
    """
    if not isinstance(tochecks, list):
        return False
    for pair in tochecks:
        name, protocol, port = pair
        if not all([isinstance(name, str), protocol.upper() in ["TCP", "UDP", "HTTP"], isinstance(port, int)]):
            return False
    return True


class PodContainer():
    def __init__(self, name="") -> None:
        self.name = name
        self.args: list[str] = None
        self.command: list[str] = None
        self.env: list[V1EnvVar] = None
        self.image: str = None
        self.ports: list[V1ContainerPort] = None
        self.volumeMounts: list[V1VolumeMount] = None
        self.workingDir: str = None
        self.readinessProbe: list[str] = None
        self.livenessProbe: list[str] = None

    def to_dict(self):
        return to_yaml(self.__dict__)

    def SetReadinessProbe(self, readinessProbe: List[str]):
        '''设置PodContainer需要的就绪探针
        可以认为一个container只需要一个就绪探针即可,[port,url path]
        '''
        if readinessProbe is None or not isinstance(readinessProbe, list):
            raise RuntimeError("PodContainer的就绪探针必须是二元字符串数组")
        if len(readinessProbe) != 2 or not all([isinstance(x, str) for x in readinessProbe]):
            raise RuntimeError("PodContainer的就绪探针必须是二元字符串数组")
        self.readinessProbe = readinessProbe

    def SetLivenessProbe(self, livenessProbe: List[str]):
        '''设置PodContainer需要的存活探针
        可以认为一个container只需要一个存活探针即可,[port,url path]
        '''
        if livenessProbe is None or not isinstance(livenessProbe, list):
            raise RuntimeError("PodContainer的存活探针必须是二元字符串数组")
        if len(livenessProbe) != 2 or not all([isinstance(x, str) for x in livenessProbe]):
            raise RuntimeError("PodContainer的存活探针必须是二元字符串数组")
        self.livenessProbe = livenessProbe


class Containerop():
    def __init__(self, name: str):
        self.name = name
        # 主容器
        self.containers: List[PodContainer] = [PodContainer("main")]
        self.labels: Dict[str, Any] = {}
        self.volumes: List[V1Volume] = []
        self.svcs: List[Tuple[str, str, str]] = []

    def add_pod_label(self, name: str, value: str):
        '''给pod增加label
        '''
        self.labels.update({name: value})

    def add_volume(self, v: V1Volume):
        '''给pod增加volume
        '''
        self.volumes.append(v)

    def add_pod_container(self, c: PodContainer):
        '''添加一个容器
        可能不止需要一个运行onceml组件的容器，方便用户添加其他容器
        '''
        self.containers.append(c)

    def add_pod_containers(self, cs: List[PodContainer]):
        '''添加一个容器
        可能不止需要一个运行onceml组件的容器，方便用户添加其他容器
        '''
        assert check_containers(
            cs), "定义的额外容器必须是class PodContainer的list'"
        self.containers += cs

    def add_svcs(self, svcs: List[Tuple[str, str, int]]):
        '''增加组件对应的svc需要开放的端口
        '''
        assert check_svc(
            svcs), "组件声明的开放端口必须是三元组（name,type,port）的list"
        for pair in svcs:
            name, protocol, port = pair
            self.svcs.append([name, protocol, str(port)])

    def to_dict(self):
        output_dict = {
            "name": self.name,
            "containers": self.containers,
            "labels": self.labels,
            "volumes": self.volumes,
            "svcs": self.svcs
        }
        return to_yaml(output_dict)


class Workflow():
    _types = {
        'apiVersion': 'str',
        'kind': 'str',
        'metadata': 'V1ObjectMeta',
        'spec': 'V1beta1CustomResourceDefinitionSpec'
    }

    def __init__(self, name: str):
        self.apiVersion = "onceml.ics.nju/v1alpha1"
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


base_types = (str, bool, int, float)


def to_yaml(obj):
    out = None
    if type(obj) == dict:
        out = {}
        # if obj.get("persistentVolumeClaim",None):
        #     print(type(obj["persistentVolumeClaim"]))
        #     print(obj)
        for var, value in obj.items():
            if value is not None:
                out[str(var)] = to_yaml(value)
    elif type(obj) == list or type(obj) == tuple:
        out = []
        for value in obj:
            out.append(to_yaml(value))

    # 基本类型
    elif isinstance(obj, base_types):
        out = obj
    # k8s类
    elif hasattr(obj, "attribute_map"):
        attribute_map = {}
        if hasattr(obj, "attribute_map"):
            attribute_map = getattr(obj, "attribute_map")
        attr_dict = {}
        for (var, value) in list(obj.__dict__.items()):
            if value is not None:
                var = var.lstrip("_")
                attr_dict[attribute_map.get(var)] = value
        return to_yaml(attr_dict)
    elif hasattr(obj, "to_dict"):
        attr_dict = {}
        for (var, value) in list(obj.__dict__.items()):
            if value is not None:
                attr_dict[var] = value
        # if attribute_map.get("persistent_volume_claim"):
        #     print(obj.to_dict())
        #     print(type(obj.persistent_volume_claim))
        #     print(attr_dict)
        #     if attr_dict.get("persistentVolumeClaim",None):
        #         print(type(attr_dict["persistentVolumeClaim"]))
        return to_yaml(attr_dict)

    return out
