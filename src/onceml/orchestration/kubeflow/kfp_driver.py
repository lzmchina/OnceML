from typing import Dict, List
import onceml.components.base.base_driver as base_driver
import onceml.components.base.base_component as base_component
class kfp_driver(base_driver.BaseDriver):
    def __init__(self, component: base_component.BaseComponent, pipeline_root: List[str], d_channels: Dict[str, str], d_artifact: Dict[str, str]) -> None:
        super().__init__(component, pipeline_root, d_channels, d_artifact)
    def run(self):
        """kfp组件的driver执行
        description
        ---------
        主要逻辑分为以下几步：

        1. 判断driver的component是否是globalcomponent，如果是，则根据他的deploytype进行下一步判断：
                - 如果是Do，则判断其alias的组件的状态是否是finished，直到其finished就结束
                - 如果是Cycle，则判断组件的phase是否是running即可退出
        2. 现在说明都是basecomponent的子类，然后根据component
        再判读其deploytype：
                - 如果是Do，则

        Args
        -------
        
        Returns
        -------
        
        Raises
        -------
        
        """
        