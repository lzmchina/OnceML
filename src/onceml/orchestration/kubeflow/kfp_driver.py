from typing import Dict, List
import onceml.components.base.base_driver as base_driver
import onceml.components.base.base_component as base_component


class kfp_driver(base_driver.BaseDriver):
    def __init__(self,**args) -> None:
        super().__init__(**args)

    def run(self):
        """kfp组件的driver执行
        description
        ---------
        主要逻辑分为以下几步：

        1. 判断driver的component是否是globalcomponent，如果是，则根据他的deploytype进行下一步判断，否则跳至2：
                - 如果是Do，则判断其alias的组件的状态是否是finished，直到其finished就跳至{}结束
                - 如果是Cycle，则判断组件的phase是否是running即可就跳至{}退出
        2. 现在说明都是basecomponent的子类，然后根据component的_changed属性判断是否需要复用之前的数据
                - _changed若为true，则说明组件发生修改，直接删除原来的数据与数据库里的state，重新创建，再跳至3
                - _changed为false，则直接复用之前的数据，并恢复数据库里的state，然后跳至4
        3. 判断_changed为true的deploytype：
                - 如果是Do，则加载依赖的组件的结果，然后执行，结束后保存state，并向后续节点发送信号
                - 如果是Cycle，则在收到依赖节点的信号，然后执行，每次执行完保存state，并向后续节点发送信号
        4. 判断_changed为false的deploytype：
                - 如果是Do，则加载依赖的组件的结果，然后执行（这里考虑到可能上次的执行由于意外没完成，方便继续执行），结束后保存state，并向后续节点发送信号
                - 如果是Cycle，则在收到依赖节点的信号，然后执行，每次执行完保存state，并向后续节点发送信号
        5. 结束
        Args
        -------
        
        Returns
        -------
        
        Raises
        -------
        
        """
        super().run('.'.join([__package__, 'kfp_ops']))
