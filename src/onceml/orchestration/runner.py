import abc
class BaseRunner(abc.ABC):
    '''基础的runner

    方便在以后进行不同编排框架的拓展，现在先做好kubeflow
    '''
    def __init__(self):
        pass
    @abc.abstractmethod
    def deploy(self,pipeline):
        """将一个pipline部署在某个编排框架里
        """
        pass