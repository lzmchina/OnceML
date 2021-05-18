import kfp
import kfp_server_api
import onceml.utils.logger as logger
import onceml.utils.cache as cache
import sys
import onceml.orchestration.kubeflow.kfp_config as kfp_config
from  onceml.orchestration.pipeline import Pipeline
def exist_experiment(client:kfp.Client,experiment_name:str):
    try:
        exp=client.get_experiment(experiment_name=experiment_name)
        logger.logger.info(exp)
        return True
    except:
        return False
def create_experiment(client:kfp.Client,experiment_name:str):
    try:
        exp=client.create_experiment(name=experiment_name)
        logger.logger.info(exp)
        return True
    except:
        return False
def ensure_experiment(client:kfp.Client,experiment_name:str):
    if exist_experiment(client=client,experiment_name=experiment_name):
        logger.logger.info('成功找到experiment：{}'.format(experiment_name))
        
    else:
        logger.logger.warning('没有找到experiment：{}'.format(experiment_name))
        logger.logger.info('开始创建experiment：{}'.format(experiment_name))
        create_experiment(client,experiment_name)
        if exist_experiment(client=client,experiment_name=experiment_name):
            logger.logger.info('创建experiment成功：{}'.format(experiment_name))
        else:
            logger.logger.error('创建experiment失败：{}'.format(experiment_name))
            raise Exception
def get_experiment_id(client:kfp.Client,experiment_name:str):
    '''获取某个experiment id
    '''
    try:
        exp=client.get_experiment(experiment_name=experiment_name)
        logger.logger.info(exp)
        return exp.id
    except:#not found
        logger.logger.error('没有找到experiment')
        return None
def exist_pipeline(client:kfp.Client,pipeline_name:str):
    '''查询某个pipeline是否有实例在运行
    '''
    exp_id=get_experiment_id(client,kfp_config.EXPERIMENT)
    if exp_id is None:
        sys.exit(1)
    pipeline_list=client.list_runs(experiment_id=exp_id)
    logger.logger.info(pipeline_list)
    return True
def ensure_pipeline(client:kfp.Client,package_path:str,pipeline:Pipeline):
    '''更新pipeline

    kubeflow的机制是每个pipeline虽然有name，但是并不是唯一，每次run一下pipeline，
    就会在name后面加一个后缀，这就阻碍了pipeline的唯一性，所以每次部署pipeline的代码后，需要将之前正在运行、或者已经结束的同一name的pipeline删除
    '''
    #if exist_pipeline()
    pass
