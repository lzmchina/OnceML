from  onceml.components import BaseExecutor
from .components import myExecutor2
import pytest
class myExecutor3(BaseExecutor):
    def Do(self, params, input_channels=None, input_artifacts=None):
        print('current component:',self.__class__)
        print(params)
        return super().Do(params, input_channels=input_channels, input_artifacts=input_artifacts)
    def Cycle(self, params, input_channels=None, input_artifacts=None):
        print('current component:',self.__class__)
        print(params)
        return super().Do(params, input_channels=input_channels, input_artifacts=input_artifacts)
class myExecutor4(BaseExecutor):
    def Cycle(self, params, input_channels=None, input_artifacts=None):
        print('current component:',self.__class__)
        print(params)
        return super().Do(params, input_channels=input_channels, input_artifacts=input_artifacts)
def test_executor_base():
    with pytest.raises(SyntaxError):
        a=BaseExecutor()
def test_executor_one_override():
    b=myExecutor2()
    c=myExecutor4()
def test_executor_two_override():
    with pytest.raises(SyntaxError):
        c=myExecutor3()