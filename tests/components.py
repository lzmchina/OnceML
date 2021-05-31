from onceml.components import BaseComponent, BaseExecutor


class myExecutor1(BaseExecutor):
    def Do(self, state, params, input_channels=None, input_artifacts=None):
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
        return {'resulta': 'fdfdf', 'resultb': 25}


class myComponent1(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)


class myExecutor2(BaseExecutor):
    def Do(self, state, params, input_channels=None, input_artifacts=None):
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
        return {
            
        }


class myComponent2(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)


class myExecutor3(BaseExecutor):
    def Do(self, state, params, input_channels=None, input_artifacts=None):
        print('current component:', self.__class__)
        print('params', params)
        print('state', state)
        print('input_channels', input_channels)
        for key, value in input_channels.items():
            print(key)
            print(value.__dict__)
        print('input_artifacts', input_artifacts)
        for key, value in input_artifacts.items():
            print(key)
            print(value.__dict__)
        return {}


class myComponent3(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)


class myExecutor4(BaseExecutor):
    def Cycle(self, state, params, input_channels=None, input_artifacts=None):
        print('current component:', self.__class__)
        print(params)
        return {}


class myComponent4(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)