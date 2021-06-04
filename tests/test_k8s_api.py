import grequests
import onceml.utils.k8s_ops as k8s_ops
import onceml.orchestration.kubeflow.kfp_config as kfp_config
import importlib

import onceml.orchestration.kubeflow.kfp_ops

def test_pod_label():
    k8s_ops = importlib.import_module('onceml.utils.k8s_ops')
    func = getattr(k8s_ops, 'get_pods_by_label')
    pod_list = func(
        namespace=kfp_config.NAMESPACE,
        label_selector="onceml.tests.task1.modela.a=1")
    for pod in pod_list:
        print(pod.status.pod_ip)
    kfp_ops = importlib.import_module('onceml.orchestration.kubeflow.kfp_ops')
    func = getattr(kfp_ops, 'get_ip_port_by_label')
    host_list = func(task_name='task1',
                     model_name='modela',
                     component_id='a')


if __name__ == "__main__":
    test_pod_label()
