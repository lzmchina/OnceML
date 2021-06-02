import onceml.utils.k8s_ops as k8s_ops
import onceml.orchestration.kubeflow.kfp_config  as kfp_config
def test_pod_label():
    pod_list = k8s_ops.get_pods_by_label(
        namespace=kfp_config.NAMESPACE,
        label_selector="{}={}".format(
            kfp_config.COMPONENT_SENDER_POD_LABEL.format(
                task='task1', model_name='modela',
                component='a'),kfp_config.COMPONENT_SENDER_POD_VALUE))