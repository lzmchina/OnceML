
import onceml.orchestration.kubeflow.kfp_driver as kfp_driver
import onceml.utils.logger as logger
import onceml.utils.json_utils as json_utils
import argparse


def main():
    logger.logger.info('开始执行组件')
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--project', type=str, required=True)
    parser.add_argument('--pipeline_root', type=str, required=True)
    parser.add_argument('--serialized_component', type=str, required=True)
    parser.add_argument('--d_channels', type=str, required=True)
    parser.add_argument('--d_artifact', type=str, required=True)
    args = parser.parse_args()
    logger.logger.info(args)

    #恢复组件
    component = json_utils.componentLoads(args.serialized_component)
    #恢复组件的一些信息
    pipeline_root = json_utils.simpleLoads(args.pipeline_root)
    d_channels = json_utils.simpleLoads(args.d_channels)
    d_artifact = json_utils.simpleLoads(args.d_artifact)
    driver = kfp_driver.kfp_driver(project=args.project,
                                   component=component,
                                   pipeline_root=pipeline_root,
                                   d_channels=d_channels,
                                   d_artifact=d_artifact)
    logger.logger.info('开始运行组件')
    driver.run()


if __name__ == '__main__':
    main()
