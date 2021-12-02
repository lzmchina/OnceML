'''
@Description	:适用于模型训练的模型封装类

@Date	:2021/08/08 14:23:20

@Author	:lzm

@version	:0.0.1
'''
import abc
from typing import Any, Dict, List
class ModelServing(abc.ABC):
    def __init__(self,model_checkpoints:str):
        """
        description
        ---------
        在初始化时会初始化你的模型，供后续的在线serving
        Args
        -------
        model_checkpoints:用于存放模型参数文件的目录，可以自行恢复模型，这里是直接传入最新timestamp的模型目录
        Returns
        -------
        
        Raises
        -------
        
        """
        
        pass

    @abc.abstractmethod
    def serving(self,json_data:str,ensemble_outout: Dict[str, str])->Any:
        """
        description
        ---------
        在收到用户的post请求后，把请求里的json字符串拿过来，用户就可以自己定义怎样处理，怎样返回预测结果了
        
        Args
        -------
        json_data:前端发来的请求服务，为json字符串，需要用户自行解析

        ensemble_outout：如果该模型有依赖其他模型，就会自动获取它们的结果并赋值在ensemble_outout字典
        
        Returns
        -------
        
        Raises
        -------
        
        """
        
        pass