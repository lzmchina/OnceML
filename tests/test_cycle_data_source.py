import onceml.types.channel as channel
from onceml.orchestration import KubeflowRunner, Pipeline
import onceml.utils.json_utils as json_utils
import onceml.global_config as global_config
import os
from onceml.components.CycleDataSource import CycleDataSource

command = [
    'python3', '-m', '{}.orchestration.kubeflow.container_entrypoint'.format(
        global_config.project_name)
]


def test_cycle_data_source():
    a = CycleDataSource(listen_data_dir="datas",
                        a=1,
                        b=2,
                        resulta=channel.OutputChannel(str),
                        resultb=channel.OutputChannel(int))
    p = Pipeline(task_name='task1', model_name='modelA', components={
        'a': a,
    })
    for component in p.components:
        arguments = [
            '--project',global_config.project_name,
            '--pipeline_root', [p._task_name, p._model_name],
            '--serialized_component',
            json_utils.componentDumps(component)
        ]
        d_channels = {}  # 获取依赖的Do类型的组件的channel输出路径
        d_artifact = {}  # 获取依赖的组件的artifact输出路径
        arguments = arguments + [
            '--d_channels', d_channels, '--d_artifact', d_artifact
        ]
        s = ''
        for i in arguments:
            s += ' '
            if type(i) == str:
                s += "'" + i + "'"
            else:
                s += "'" + json_utils.simpleDumps(i) + "'"
        print('------------')
        os.system(' '.join(command) + s)


if __name__ == "__main__":
    test_cycle_data_source()
