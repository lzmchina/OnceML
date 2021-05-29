import kfp
import kfp_server_api
import onceml.utils.logger as logger
import onceml.utils.cache as cache
import sys
import os
import onceml.types.exception as exception
import onceml.orchestration.kubeflow.kfp_config as kfp_config
from onceml.orchestration.pipeline import Pipeline
import onceml.utils.k8s_ops as k8s_ops
import onceml.utils.db as db
import onceml.global_config as global_config
import onceml.components.base.global_component as global_component
import onceml.types.phases as phases

def exist_experiment(client: kfp.Client, experiment_name: str):
    try:
        exp = client.get_experiment(experiment_name=experiment_name)
        return True
    except:
        return False


def create_experiment(client: kfp.Client, experiment_name: str):
    try:
        exp = client.create_experiment(name=experiment_name)
        return True
    except:
        return False


def ensure_experiment(client: kfp.Client, experiment_name: str):
    if exist_experiment(client=client, experiment_name=experiment_name):
        logger.logger.info('成功找到experiment：{}'.format(experiment_name))

    else:
        logger.logger.warning('没有找到experiment：{}'.format(experiment_name))
        logger.logger.info('开始创建experiment：{}'.format(experiment_name))
        create_experiment(client, experiment_name)
        if exist_experiment(client=client, experiment_name=experiment_name):
            logger.logger.info('创建experiment成功：{}'.format(experiment_name))
        else:
            logger.logger.error('创建experiment失败：{}'.format(experiment_name))
            raise Exception


def get_experiment_id(client: kfp.Client, experiment_name: str):
    '''获取某个experiment id
    '''
    try:
        exp = client.get_experiment(experiment_name=experiment_name)

        return exp.id
    except:  # not found
        logger.logger.error('没有找到experiment')
        return None


def exist_pipeline(client: kfp.Client, pipeline_name: str) -> list:
    '''查询某个pipeline是否有workflow实例在运行
    '''
    exp_id = get_experiment_id(client, kfp_config.EXPERIMENT)
    if exp_id is None:
        sys.exit(1)
    run_list = client.list_runs(
        experiment_id=exp_id, page_size=kfp_config.RUNS_PAGE_SIZE).runs or []
    pipeline_list = []
    for run in run_list:
        if pipeline_name in run.name:
            pipeline_list.append(run.id)
    logger.logger.info('当前项目已有的实例:{}'.format(pipeline_list))
    return pipeline_list


def ensure_pipeline(client: kfp.Client, package_path: str, pipeline: Pipeline):
    '''更新pipeline

    kubeflow的机制是每个pipeline虽然有name，但是并不是唯一，每次run一下pipeline，
    就会在name后面加一个后缀，这就阻碍了pipeline的唯一性，所以每次部署pipeline的代码后，需要将之前正在运行、或者已经结束的同一name的pipeline删除
    '''
    instances = exist_pipeline(client,'-'.join(
        [global_config.PROJECTDIRNAME, pipeline.id]))
    if len(instances) > 0:  # 说明有实例，先删除
        for instance in instances:
            logger.logger.info('删除已有的run实例:{}'.format(instance))
            workflowlist = k8s_ops.get_crd_instance_list(
                namespace=kfp_config.NAMESPACE,
                group=kfp_config.wf_group,
                label_selector='pipeline/runid={}'.format(instance),
                version=kfp_config.wf_version,
                plural=kfp_config.wf_plural
            )['items'] or []
            for wf in workflowlist:
                k8s_ops.delete_crd_instance(
                    namespace=kfp_config.NAMESPACE,
                    group=kfp_config.wf_group,
                    version=kfp_config.wf_version,
                    plural=kfp_config.wf_plural,
                    name=wf["metadata"]['name']
                )
            #最后再删除run
            client._run_api.delete_run(id=instance)
    # 为0，说明该pipeline是第一次创建或者是被用户使用其他方法手动删除了，这时需要在数据库里删除相应信息

    # 然后再创建
    client.create_run_from_pipeline_package(pipeline_file=package_path,
                                            arguments={},
                                            run_name='-'.join(
                                                [global_config.PROJECTDIRNAME, pipeline.id]),
                                            experiment_name=kfp_config.EXPERIMENT,
                                            )
    #


def ensure_pv(rootdir: str, nfc_host: str):
    '''创建供onceml使用的pv
    '''
    pv_name = kfp_config.PVNAME_PRE+'-'+global_config.PROJECTDIRNAME
    pv_info = k8s_ops.get_pv(pv=pv_name)
    nfc_host = nfc_host or k8s_ops.get_current_node_host()
    if nfc_host is None:
        logger.logger.error('nfc host没找到，请手动设置')
        raise exception.NFCNotFoundError
    nfsurl = [nfc_host, rootdir]
    if pv_info is None:
        # 说明集群里没有相应的pv
        logger.logger.warning('没有找到pv：{},现在开始创建'.format(pv_name))
        if not k8s_ops.create_nfs_pv(pvname=pv_name, nfsurl=nfsurl, labels={
            kfp_config.PV_LABEL: global_config.PROJECTDIRNAME
        }):
            logger.logger.error('创建pv ：{}失败'.format(pv_name))
            raise RuntimeError
        else:
            logger.logger.info('创建pv ：{}成功！'.format(pv_name))
    else:
        # 找到了，需要检查是否跟工程的目录匹配
        logger.logger.warning('目前pv：{}的host与url与当前不符'.format(pv_name))


def ensure_nfs_server(NFS_NAME: str, labels: dict):
    '''创建项目的nfs server与svc，保证所有的task都能共享
    '''
    logger.logger.info("开始创建nfs server,挂载目录:{}".format(global_config.PROJECTDIR))
    k8s_ops.apply_nfs_server(NFS_NAME, labels)


def ensure_nfs_svc(NFS_SVC_NAME: str, selector: dict):
    '''创建项目的nfs server与svc，保证所有的task都能共享
    '''
    logger.logger.info("开始创建nfs server svc:{}".format(NFS_SVC_NAME))
    k8s_ops.apply_nfs_svc(NFS_SVC_NAME, selector)


def change_pipeline_phase_to_created(pipeline_id: str):
    '''将pipeline的phase切换至created
    '''
    db.update('.'.join(['kfp', pipeline_id.replace('_', '.'), 'phase']),
              phases.PIPELINE_PHASES.CREATED.value)


def change_pipeline_phase_to_running(pipeline_id: str):
    '''将pipeline的phase切换至running
    '''
    db.update('.'.join(['kfp', pipeline_id.replace('_', '.'), 'phase']),
              phases.PIPELINE_PHASES.RUNNING.value)


def change_pipeline_phase_to_finished(pipeline_id: str):
    '''将pipeline的phase切换至finished
    '''
    db.update('.'.join(['kfp', pipeline_id.replace('_', '.'), 'phase']),
              phases.PIPELINE_PHASES.FINISHED.value)


def change_components_phase_to_created(pipeline_id: str, component_id: str):
    '''将某个组件的状态改变至created
    '''
    db.update('.'.join(['kfp', pipeline_id.replace('_', '.'), component_id,
              'phase']), phases.Component_PHASES.CREATED.value)


def change_components_phase_to_running(pipeline_id: str, component_id: str):
    '''将某个组件的状态改变至running
    '''
    db.update('.'.join(['kfp', pipeline_id.replace('_', '.'), component_id,
              'phase']), phases.Component_PHASES.RUNNING.value)


def change_components_phase_to_finished(pipeline_id: str, component_id: str):
    '''将某个组件的状态改变至finished
    '''
    db.update('.'.join(['kfp', pipeline_id.replace('_', '.'), component_id,
              'phase']), phases.Component_PHASES.FINISHED.value)


def get_global_component_alias_component(task_name: str, model_name: str, component: global_component.GlobalComponent):
    '''获得global_component的原始model、component
    '''
    alias_model = db.select(
        '.'.join([task_name, model_name, component.id, 'alias_model']))
    alias_component = db.select(
        '.'.join([task_name, model_name, component.id, 'alias_component']))
    return alias_model, alias_component
