# -*- encoding: utf-8 -*-
'''
@Description	:提取task里全局共享的组件

@Date	:2021/05/17 20:02:06

@Author	:lzm

@version	:0.0.1
'''
from typing import Optional,List
import onceml.components.base as base
class GlobalComponent(base.BaseComponent):
    def __init__(self, alias_model_name:str,alias_component_id:str,inputs: Optional[List] = None):
        """获取全局共享组件
        description
        ---------
        
        Args
        -------
        model_name:从哪个model里面获取组件

        component_id：组件的id

        Returns
        -------
        
        Raises
        -------
        
        """
        self._alias_model_name=alias_model_name
        self._alias_component_id=alias_component_id
        super().__init__(executor=base.BaseExecutor,inputs=inputs,shared=True)
    @property
    def alias_model_name(self):
        return self._alias_model_name
    
    @property
    def alias_component_id(self):
        return self._alias_component_id
