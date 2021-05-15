from onceml.components import BaseComponent,BaseExecutor
class myExecutor1(BaseExecutor):
    def Do(self, params, input_channels=None, input_artifacts=None):
        print('current component:',self.__class__)
        print(params)
        return super().Do(params, input_channels=input_channels, input_artifacts=input_artifacts)
class myComponent1(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)
class myExecutor2(BaseExecutor):
    def Do(self, params, input_channels=None, input_artifacts=None):
        print('current component:',self.__class__)
        print(params)
        return super().Do(params, input_channels=input_channels, input_artifacts=input_artifacts)
class myComponent2(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)
class myExecutor3(BaseExecutor):
    def Do(self, params, input_channels=None, input_artifacts=None):
        print('current component:',self.__class__)
        print(params)
        return super().Do(params, input_channels=input_channels, input_artifacts=input_artifacts)
class myComponent3(BaseComponent):
    def __init__(self, executor, inputs=None, **args):
        super().__init__(executor=executor, inputs=inputs, **args)