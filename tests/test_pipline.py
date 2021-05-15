from onceml.orchestration import Pipline

import pytest
from .components import myComponent1, myComponent2, myComponent3, myExecutor2, myExecutor1, myExecutor3


def test_pipline_parameter():
    print(type(Pipline))
    with pytest.raises(TypeError):
        Pipline(task_name='1', model_name=2)
    with pytest.raises(TypeError):
        Pipline(task_name=1, model_name='2', components=[])


def test_pipline_runtime():
    a = myComponent1(executor=myExecutor1, a=1, b=2)
    b = myComponent2(executor=myExecutor2, inputs=[a], a=6, s=3)
    c = myComponent3(executor=myExecutor3, inputs=[a, b])

    p = Pipline(task_name='test', model_name='4', components={
        'a': a,
        'b': b,
        'c': c
    })
    p._testrun()
