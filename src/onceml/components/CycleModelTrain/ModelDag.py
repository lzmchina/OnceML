from posixpath import expanduser
from typing import Any, Dict, List
import onceml.utils.db as db
import onceml.utils.topsort as toposort
import json
Dag_key = "model.dag.{}"
Version_key = "model.version.{task}.{model}"


class ModelNode:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.up_models = []  # type: List[ModelNode]
        self.down_models = []  # type: List[ModelNode]

    def append_up_model(self, up_model):
        """添加上游model，即依赖的model
        """
        if up_model is None:
            return
        self.up_models.append(up_model)

    def append_down_model(self, down_model):
        """添加下游model，即模型更新时，将更新消息发送至下游模型
        """
        if down_model is None:
            return
        self.down_models.append(down_model)

    def __str__(self) -> str:
        return "{}----->{}".format(
            ",".join([node.model_name for node in self.up_models]),
            self.model_name
        )

    def __repr__(self) -> str:
        return self.__str__()


def model_topo_to_str(models: List[ModelNode]) -> str or Any:
    """将拓扑结构转为字符串
    """
    model_layers = toposort.topsorted_layers(
        models,
        get_node_id_fn=lambda x: x.model_name,
        get_parent_nodes=lambda x: x.up_models,
        get_child_nodes=lambda x: x.down_models
    )
    store_layers = []  # type: List[List[ModelNode]]
    for layer in model_layers:
        layer_models = []  # type: List[ModelNode]
        for model in layer:
            layer_models.append({
                "model": model.model_name,
                "up_models": ",".join([node.model_name for node in model.up_models]),
                "down_models": ",".join([node.model_name for node in model.down_models])
            })
        store_layers.append(layer_models)
    return json.dumps(store_layers)


def str_to_model_topo(str: str) -> List[List[ModelNode]]:
    """从字符串恢复到模型拓扑图
    """
    retrieve_layers = None  # type: List[List[Dict]]
    if str != None:
        retrieve_layers = json.loads(str)

    model_layers = []  # type: List[List[ModelNode]]
    if retrieve_layers is None:
        return model_layers
    k = {}  # type: Dict[str,ModelNode]
    for layer in retrieve_layers:
        model_layer = []
        for layer_model in layer:
            node = ModelNode(model_name=layer_model["model"])
            k[node.model_name] = node
            model_layer.append(node)
        model_layers.append(model_layer)
    for layer in retrieve_layers:
        for layer_model in layer:

            node = k[layer_model["model"]]

            up_nodes = layer_model["up_models"].split(",")

            for up_node in up_nodes:

                node.append_up_model(k.get(up_node))
            down_nodes = layer_model["down_models"].split(",")
            for down_node in down_nodes:
                node.append_down_model(k.get(down_node))
    return model_layers


def getModelTopoDag(task_name: str):
    """
    获取模型依赖Dag图
    """
    model_layers = str_to_model_topo(db.select(Dag_key.format(task_name)))
    return model_layers


def saveModelTopoDag(task_name: str, models: List[ModelNode]):
    dag_str = model_topo_to_str(models)
    db.update(Dag_key.format(task_name), dag_str)


def getModelNodeList(task_name: str):
    """以list的形式返回模型依赖图
    """
    model_layers = getModelTopoDag(task_name=task_name)
    models = []  # type: List[ModelNode]
    for layer in model_layers:
        models += layer
    return models


def getModelNode(task_name: str, model_name: str):
    """获取model对应的ModelNode
    """
    models = getModelNodeList(task_name=task_name)
    for model in models:
        if model.model_name == model_name:
            return model
    return None


def updateModelDag(task_name: str, model_nodes: List[ModelNode]):
    """将若干个model进行dag的更新
    """
    exist_models = getModelNodeList(task_name=task_name)
    new_models_dict = {}
    for model in model_nodes:
        new_models_dict[model.model_name] = model
    news = []
    for exist_model in exist_models:
        if new_models_dict.get(exist_model.model_name) is None:
            news.append(exist_model)
    news += model_nodes
    saveModelTopoDag(task_name=task_name, models=news)


def updateUpStreamNode(task_name: str, model_name: str, up_stream_models: List[str]):
    """更新model的上游模型
    """
    curnode = getModelNode(task_name=task_name, model_name=model_name)
    if curnode is None:
        curnode = ModelNode(model_name=model_name)
    # 清理旧的上游模型信息
    curnode.up_models = []
    upnodes = []
    for upmodel in up_stream_models:
        upnode = getModelNode(task_name=task_name, model_name=upmodel)
        if upnode is None:
            upnode = ModelNode(model_name=upmodel)
        exist = False
        for node in upnode.down_models:
            if node.model_name == curnode.model_name:
                exist = True
                break
        if not exist:
            upnode.append_down_model(curnode)
        exist = False
        curnode.append_up_model(upnode)
        upnodes.append(upnode)
    upnodes.append(curnode)
    updateModelDag(task_name, upnodes)


def getRuntimeModelTopoDag(task_name: str):
    """在runtime里获取dag图

    与getModelTopoDag的区别：
    实际的kv存储里，每个modelnode只会存放上游节点，不会存放下游节点
    但是在runtime时，还要得到下游节点信息，这样方便进行信号通知
    """
    models = getModelNodeList(task_name=task_name)
    k = {}  # type: Dict[str,ModelNode]
    for model in models:
        k[model.model_name] = model
    for model in models:
        for up_node in model.up_models:
            k[up_node].append_down_model(model.model_name)
    return models


def saveModelVersion(task_name: str, model: str, v: int):
    """记录模型的版本
    每次模型完成一个迭代后，将模型版本信息存储在kv数据库里

    读：任意模型generator组件都可以读

    写：只能由相应的generator组件进行写
    """
    db.update(Version_key.format({
        "task": task_name,
        "model": model
    }),v)
