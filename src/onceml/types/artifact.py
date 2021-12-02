# -*- encoding: utf-8 -*-
'''
@Description	: 

@Date	:2021/04/19 15:49:47

@Author	:lzm

@version	:0.0.1
'''
import onceml.utils.json_utils as json_utils


class Artifact(json_utils.Jsonable):
    """Artifact只组件产生的数据文件

    如果说Channel是针对轻量级数据，Artifact则是指比较的的数据文件，例如数据集、模型文件等，Artifact也是Component的重要组成部分，我们只需要指定组件的产生文件位置在哪就行（比如NFS，或者是容器里挂载的目录） 
    """
    def __init__(self, url: str = None):
        self._url = url or ''

    @property
    def url(self):
        return self._url

    def setUrl(self, url: str):
        if not isinstance(url, str):
            raise TypeError("Artifact设置的url应该是一个str类型的变量")
        self._url = url

    def to_json_dict(self):
        return self.__dict__