# -*- encoding: utf-8 -*-
'''
@Description	:适用于模型训练的模型封装类

@Date	:2021/08/08 14:23:20

@Author	:lzm

@version	:0.0.1
'''

import abc
from types import List
class ModelGenerator(abc.ABC):
    def __init__(self,model_checkpoints:str):
        """
        description
        ---------
        在初始化时会初始化你的模型，供后续的训练、验证、预测
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
    def filter(self):
        """
        description
        ---------
        用于对特征工程组件产生的数据进行筛选，返回一个二元组（start timestamp,end timestamp）timestamp是特征工程里用户标记的，精确到秒即可
        如果没有限制，就直接返回None，这个区间为闭区间
        
        Args
        -------
        
        Returns
        -------
        (start timestamp,end timestamp):起始时间与结束时间
        Raises
        -------
        
        """
        
        pass
    @abc.abstractmethod
    def train(self,file_list:List):
        """
        description
        ---------
        用于训练并产生一个模型
        Args
        -------
        file_list：包含此次用于模型训练的文件url数组，可以是经过timestamp筛选后的文件，也可以是所有文件
        
        
        Returns
        -------
        
        Raises
        -------
        
        """
        
        pass
    @abc.abstractmethod
    def model_save(self,model_checkpoints:str):
        """
        description
        ---------
        这个函数是用来保存模型的，用户需要在这里面定义怎样保存模型，以及其他的一些数据文件
        
        通常，这个函数是在执行一次train方法后进行调用
        Args
        -------
        model_checkpoints:用于存放训练完毕后的目录，是一个以时间戳命名的目录
        Returns
        -------
        
        Raises
        -------
        
        """
        
        pass
    @abc.abstractmethod
    def predict(self,x_datas:list)->list:
        """
        description
        ---------
        用于对外进行模型集成的服务,只需要将x_datas视为模型的输入，返回相应的结果即可
        Args
        -------
        
        Returns
        -------
        
        Raises
        -------
        
        """
        
        pass
    @abc.abstractmethod
    def eval(self,file_list:List)->bool:
        """
        description
        ---------
        在已经存在一个模型的时候，如果新到来的数据经过这个eval验证，用户可以定义验证的过程，返回一个bool值，如果为true，则重新训练一个新模型，如果false，则跳过
        Args
        -------
        
        Returns
        -------
        bool:是否需要再次训练，产生一个新模型
        
        Raises
        -------
        
        """
        
        pass
