from onceml.orchestration import KubeflowRunner,Pipeline
from components import myComponent1,myComponent2,myComponent3,myExecutor2,myExecutor1,myExecutor3
import onceml.types.channel as channel
import onceml.utils.k8s_ops as k8s_ops
import onceml.orchestration.kubeflow.kfp_config as kfp_config
from onceml.components.base.global_component import GlobalComponent
def test_kfp_global_component():
    a=GlobalComponent(alias_model_name='modelA',alias_component_id='a')
    p=Pipeline(task_name='task1',model_name='modelB',components={
        'a':a,
    }
    )
    KubeflowRunner().deploy(pipeline=p)
if __name__ == "__main__":
    test_kfp_global_component()