from onceml.orchestration import KubeflowRunner,Pipeline
from components import myComponent1,myComponent2,myComponent3,myExecutor2,myExecutor1,myExecutor3
import onceml.types.channel as channel
import onceml.utils.k8s_ops as k8s_ops
import onceml.utils.json_utils as json_utils
import onceml.global_config as global_config
import onceml.orchestration.kubeflow.kfp_config as kfp_config
from onceml.components.base.global_component import GlobalComponent
import os
command=['python3','-m','{}.orchestration.kubeflow.container_entrypoint'.format(
    global_config.project_name)]
def test_container_entrypoint():
    a=myComponent1(executor=myExecutor1,a=1,b=2,resulta=channel.OutputChannel(str),resultb=channel.OutputChannel(int))
    b=myComponent2(executor=myExecutor2,inputs=[a],a=6,s=3)
    c=myComponent3(executor=myExecutor3,inputs=[a,b])
    p=Pipeline(task_name='task1',model_name='modelA',components={
        'a':a,
        'b':b,
        'c':c
    }
    )
    for component in p.components:
        arguments = [
            '--pipeline_root',
            [p._task_name,p._model_name],
            '--serialized_component',
            json_utils.componentDumps(component)
        ]
        d_channels = {'a':'out/a'}  # 获取依赖的Do类型的组件的channel输出路径
        d_artifact = {'b':'out/b'}  # 获取依赖的组件的artifact输出路径
        arguments = arguments+[
            '--d_channels',
            d_channels,
            '--d_artifact',
            d_artifact
        ]
        s=''
        for i in arguments:
            s+=' '
            if type(i)==str:
                s+=  "'"+i +"'"
            else:
                s+= "'"+json_utils.simpleDumps(i)+"'"
        os.system(' '.join(command)+s)
if __name__ == "__main__":
    test_container_entrypoint()