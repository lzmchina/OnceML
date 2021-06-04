import time
from onceml.components.base import BaseComponent, BaseExecutor
class myExecutor1(BaseExecutor):
    def Cycle(self, state, params, data_dir,input_channels=None, input_artifacts=None):
        print('current component:', self.__class__)
        print('params', params)
        print('state', state)
        print('input_channels', input_channels)
        print('input_artifacts', input_artifacts)
        for key, value in input_channels.items():
            print(key)
            print(value.__dict__)
        print('input_artifacts', input_artifacts)
        for key, value in input_artifacts.items():
            print(key)
            print(value.__dict__)
        time.sleep(60)
        return {'resulta': 'fdfdf', 'resultb': 25}

    def pre_execute(self):
        print('this is pre_execute')


class myComponent1(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)