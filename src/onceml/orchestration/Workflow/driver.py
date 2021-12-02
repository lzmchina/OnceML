from typing import Dict, List
import onceml.components.base.base_driver as base_driver
import onceml.components.base.base_component as base_component


class onceml_driver(base_driver.BaseDriver):
    def __init__(self,**args) -> None:
        super().__init__(**args)

    def run(self):
        """组件的driver执行
        """
        super().run()
