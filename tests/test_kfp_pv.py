import onceml.orchestration.kubeflow.kfp_ops as kfp_ops
import os
if __name__ == "__main__":
    kfp_ops.ensure_pv(os.getcwd(),None)