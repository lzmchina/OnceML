from typing import Dict, Optional
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.types.artifact import Artifact
from onceml.types.channel import Channels
from onceml.types.state import State


class _executor(BaseExecutor):
    def __init__(self):
        super().__init__()

    def Cycle(self, state: State, params: dict, data_dir, input_channels: Optional[Dict[str, Channels]] = None, input_artifacts: Optional[Dict[str, Artifact]] = None) -> Channels:
        pass

    def pre_execute(self, state: State, params: dict, data_dir: str):
        return super().pre_execute(state, params, data_dir)


class CycleModelServing(BaseComponent):
    def __init__(self, model_generator_component: BaseComponent, emsemble_models: list = [], **args):
        """多副本部署模型
        接收modelGenerator的更新的模型的消息，从而对部署的模型进行滚动更新
        """
        super().__init__(executor=_executor, inputs=model_generator_component,
                         emsemble_models=emsemble_models, **args)
        self.state = {
            "model_checkpoint": -1,  # 只对验证有作用
        }
