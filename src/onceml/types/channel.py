# -*- encoding: utf-8 -*-
'''
@Description	:

@Date	:2021/04/19 15:50:10

@Author	:lzm

@version	:0.0.1
'''
import onceml.utils.json_utils as json_utils


class Channels(json_utils.Jsonable):
    """Channels是一种数据交换格式，可以理解为内置了字典的class，提供了数据的序列化与反序列化

    组件之间需要交换轻量级的数据，比如环境配置、执行的参数等。因此Channel负责将数据序列化，作为Component的一部分（input、output）。
    当不同组件之间需要交换数据时，Component将发送给后续的组件Component,
    
    """
    def __init__(self, data: dict=None):
        if data is not None and not isinstance(data, dict):
            raise TypeError
        self._data = data

    def update(self, key, value):
        self._data.update({key: value})

    def to_json_dict(self):
        return self.__dict__.items()
    def __getitem__(self,key):
        return self._data.get(key)

class OutputChannel(json_utils.Jsonable):
    """OutputChannel是Channels的一个key-value对

    由于不同组件运行在不同的进程里、节点里，因此需要对数据进行序列化，尤其是Channels这种直接交互的数据；因此对value的数据类型
    要做限制，要能够直接被json序列化、反序列化。
    """
    def __init__(self, ctype: type):
        if ctype not in [int, float, dict, str, list]:
            raise TypeError('不是支持的基本数据类型，建议先自行序列化')
        self._type = ctype

    def to_json_dict(self):
        return self.__dict__.items()
