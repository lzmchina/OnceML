from onceml.components.base.global_component import GlobalComponent
from onceml.orchestration import KubeflowRunner, Pipeline
import onceml.utils.json_utils as json_utils
import os
import onceml.global_config as global_config
command = [
    'python3', '-m', '{}.orchestration.kubeflow.container_entrypoint'.format(
        global_config.project_name)
]


def test_global_component():
    a = GlobalComponent(alias_model_name='modela', alias_component_id='c')
    p = Pipeline(task_name='task1', model_name='modelB', components={
        'c': a,
    }
    )
    for component in p.components:
        arguments = [
            '--pipeline_root', [p._task_name, p._model_name],
            '--serialized_component',
            json_utils.componentDumps(component)
        ]
        d_channels = {
            'a': 'task1/modela/a/result.json',
        }  # 获取依赖的Do类型的组件的channel输出路径
        d_artifact = {
            'a': 'task1/modela/a/artifact',
            'b': 'task1/modela/b/artifact',
        }  # 获取依赖的组件的artifact输出路径
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
    test_global_component()
