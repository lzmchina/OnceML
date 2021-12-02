import onceml.types.channel as channel
from onceml.orchestration import KubeflowRunner, Pipeline

import os
from cycle_component import myComponent1, myExecutor1, myComponent2, myExecutor2


def test_container_entrypoint():
    a = myComponent1(executor=myExecutor1,
                     a=1,
                     b=2,
                     resulta=channel.OutputChannel(str),
                     resultb=channel.OutputChannel(int))
    b = myComponent2(executor=myExecutor2,
                     a=1,
                     b=2,
                     resulta=channel.OutputChannel(str),
                     resultb=channel.OutputChannel(int),
                     inputs=[a])
    p = Pipeline(task_name='task1',
                 model_name='modelA',
                 components={
                     'a': a,
                     'b': b
                 })

    KubeflowRunner(docker_image='liziming/onceml:latest').deploy(pipeline=p)


if __name__ == "__main__":
    test_container_entrypoint()
