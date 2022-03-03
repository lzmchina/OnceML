# -*- encoding: utf-8 -*-
'''
@Description	:缓存机制

@Date	:2021/05/16 21:13:08

@Author	:lzm

@version	:0.0.1
'''
def judge_update(before_component,
                 current_component):
    '''判断先后两个组件是否可以进行数据复用

    @Date	:2021/10/21 01:29:16

    组件的缓存什么时候该复用呢？updates布尔变量的取值

    首先从以下三个方面考虑

    - 组件自身是否有变化？selfchanged：true/false 
        - 输入参数

    - 组件依赖的组件列表是否有变化？

        假定上次依赖[b,c],这次也是[b,c],但是b的updated变成true，因此本组件也要认为更新了
    - 组件的拓扑结构 topo_changed:true/false
        - 位于的层次
        - 依赖的组件列表是否变了：之依赖[a,b],现在依赖[b,c],这就变了
    '''
    selfChanged = False
    # case 1:组件自身是否有变化？
    if before_component._params != current_component._params:
        selfChanged = True
    # case 3:组件依赖的组件列表是否有变化
    topoChanged = False
    lastList = list(before_component.upstreamComponents).sort()
    # print(list(current_component.upstreamComponents))
    # for x in list(current_component.upstreamComponents):
    #     print(x.id)
    currentList = list([x.id for x in list(current_component.upstreamComponents)]).sort()
    if lastList != currentList or before_component.topoLayerIndex != current_component.topoLayerIndex:
        topoChanged = True
    # case 2: 组件的拓扑结构发生变化
    upstreamComponentListChanged = False
    for up in current_component.upstreamComponents:
        if up.changed:
            upstreamComponentListChanged = True
            break
    return selfChanged or topoChanged or upstreamComponentListChanged
