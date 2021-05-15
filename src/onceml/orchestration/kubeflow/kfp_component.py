from kfp import dsl
from typing import Set

from onceml.components import BaseComponent
class kfpComponent:
    '''kubeflow workflow中的一个组件

    将pipline的组件转化至kfpComponent，包含执行的命令、使用的镜像、挂载的pv等信息
    '''
    def __init__(self,component:BaseComponent,depends_on:Set[dsl.ContainerOp]):
        """kubeflow component的表示
        description
        ---------
        kubeflow需要组件返回dsl.ContainerOp，这个类就是包装，同时还有其他信息，最终返回一个dsl.ContainerOp

        Args
        -------
        component：本框架的component

        depends_on： component依赖的其他 component的ContainerOp
        
        Returns
        -------
        
        Raises
        -------
        
        """
        
