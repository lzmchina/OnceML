# -*- encoding: utf-8 -*-
'''
@Description	:缓存机制

@Date	:2021/05/16 21:13:08

@Author	:lzm

@version	:0.0.1
'''
import onceml.components.base.base_component as base_component


def judge_update(before_component: base_component.BaseComponent,
                 current_component: base_component.BaseComponent):
    '''判断先后两个组件是否可以进行数据复用
    todo:更复杂的比较，比如代码变更等
    现在就见到的比较数据参数
    '''
    if before_component._params == current_component._params:
        return False
    return True
