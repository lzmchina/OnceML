import os
import re
import sys
import time

from onceml.utils import k8s_ops, logger, pipeline_utils
import onceml.configs.k8sConfig as k8sConfig
import onceml.global_config as global_config

_MIN_INT = -9999999
_MAX_INT = sys.maxsize


def checkModelList(taskname, modelList, records):
    '''获得需要请求的model list
    本模型会记录每次调用的模型的checkpoint，初始值为-1，当模型需要训练时，可向数据库里查询modelList，如果他们的checkpoint全部大于-1,
    说明他们有产生过模型，然后才能与他们通信;否则就轮询，直到他们有模型
    '''
    logger.logger.info("开始搜索依赖的模型的checkpoint")
    while True:
        need_use = []
        for model in modelList:
            latest_checkpoint = getModelCheckpointFromDb(taskname, model)
            logger.logger.info("模型：{} 的最新checkpoint为{}".format(
                model, latest_checkpoint))
            if latest_checkpoint > -1:
                need_use.append(model)
        if len(need_use) == len(modelList):
            return need_use
        else:
            time.sleep(5)


def diffFileList(exist_file_dir: str, req_file_list: list):
    '''用来寻找需要处理的文件的list
    组件在收到集成模型的请求后，拿到file list，可以做一个diff，筛选一下
    '''
    exist_files = os.listdir(exist_file_dir)
    return list(set(req_file_list).difference(set(exist_files)))


def getTimestampFilteredFile(dir, file_pattern, start_timestamp, end_timestamp,
                             end_file_id):
    '''获得符合时间戳条件的文件
    '''
    file_name_pattern = re.compile(file_pattern)
    filtered_list = []
    filtered_list_with_prefix = []
    if start_timestamp is None:
        start_timestamp = _MIN_INT
    if end_timestamp is None:
        end_timestamp = _MAX_INT
    for file in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, file)):
            timastamp_str, file_id = os.path.splitext(file)[0].split(
                '-')[0], int(os.path.splitext(file)[0].split('-')[1])
            if timastamp_str == '':
                if file_id <= end_file_id:
                    filtered_list.append(file)
                    filtered_list_with_prefix.append(os.path.join(dir, file))
            else:
                timestamp = int(timastamp_str)
                if timestamp >= start_timestamp and timestamp <= end_timestamp:
                    if file_id <= end_file_id:
                        filtered_list.append(file)
                        filtered_list_with_prefix.append(
                            os.path.join(dir, file))
    return filtered_list_with_prefix, filtered_list


def getEvalSampleFile(dir, file_pattern, start_file_id, end_file_id):
    '''获取验证模型用的文件list

    返回二元组：文件包含目录路径的list，文件名的list
    '''
    file_name_pattern = re.compile(file_pattern)
    filtered_list_with_prefix = []
    filtered_list = []
    for file in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, file)):
            id = int(os.path.splitext(file)[0].split('-')[1])
            if id > start_file_id and id <= end_file_id:
                filtered_list_with_prefix.append(os.path.join(dir, file))
                filtered_list.append(file)
    return filtered_list_with_prefix, filtered_list


def getPodLabelValue(task_name, model_list):
    '''获取某个pod的标签value
    保证每个组件都能获得label value
    '''
    model_pod_label = {}
    for model in model_list:
        ensure = False
        while not ensure:
            component_id = pipeline_utils.get_pipeline_model_component_id(
                task_name=task_name, model_name=model)
            logger.logger.info("模型：{} 的模型组件为：{}".format(model, component_id))
            if component_id is not None:
                ensure = True
                model_pod_label[model] = component_id
            else:
                time.sleep(5)
    return model_pod_label


def getPodIpByLabel(label_dict: dict, namespace):
    '''根据标签，获得对应组件pod的ip
    保证host里面每一个均是有效的ip，然后才返回
    '''
    model_hosts = {}
    for model, label in label_dict.items():
        ensure = False
        while not ensure:
            logger.logger.info("{}={}".format(k8sConfig.COMPONENT_POD_LABEL,
                                              label))
            pod_list = k8s_ops.get_pods_by_label(
                namespace=namespace,
                label_selector="{}={}".format(k8sConfig.COMPONENT_POD_LABEL,
                                              label))
            host_list = [pod.status.pod_ip for pod in pod_list]
            logger.logger.info("模型：{} 的模型组件host为：{}".format(
                model, ",".join(host_list)))
            if len(host_list) > 0 and all([x[0] for x in host_list]):
                ensure = True
                model_hosts[model] = host_list[0]
            else:
                time.sleep(5)
    return model_hosts


def updateModelCheckpointToDb(task_name, model, checkpoint: int):
    '''将模型的最新checkpoint更新到数据库里
    '''
    pipeline_utils.update_model_checkpoint(task_name, model, str(checkpoint))


def getModelCheckpointFromDb(task_name, model):
    '''获取数据库里某个task的模型最新checkpoint
    '''
    checkpoint = pipeline_utils.get_model_checkpoint(task_name, model)
    if checkpoint is None:
        return -1
    else:
        return int(checkpoint)


def getModelDir(task_name, model_name, checkpoint: int):
    """获得模型某个checkpoint的目录
    """
    component_id = pipeline_utils.get_pipeline_model_component_id(
        task_name, model_name).split(".")[-1]
    artifact_dir=pipeline_utils.get_pipeline_component_artifact_url(task_name, model_name,component_id)
    return os.path.join(artifact_dir,'checkpoints',str(checkpoint))
