from typing import List
import onceml.utils.db as db
import onceml.utils.cache as cache
import onceml.utils.json_utils as json_utils
import onceml.components.base.base_component as base_component
import onceml.components.base.global_component as global_component
import onceml.types.phases as phases
import os
import onceml.global_config as global_config
import onceml.types.component_msg as component_msg


def parse_component_to_container_entrypoint(component: base_component,
                                            task_name: str,
                                            model_name: str,
                                            Do_deploytype: List[str],
                                            project_name=None):
    """将组建解析成容器运行时的序列化字符串
    """
    arguments = [
        '--project', project_name or global_config.PROJECTDIRNAME,
        '--pipeline_root',
        json_utils.simpleDumps([task_name,
                                model_name]), '--serialized_component',
        json_utils.componentDumps(component)
    ]
    d_channels = {}  # 获取依赖的Do类型的组件的channel输出路径
    d_artifact = {}  # 获取依赖的组件的artifact输出路径
    for c in component.upstreamComponents:
        if type(c) == global_component.GlobalComponent:
            #如果是全局组件，他的目录就应该用真实的别名的组件的目录
            if c.id in Do_deploytype:
                d_channels[c.id] = os.path.join(
                    c.artifact.url,
                    component_msg.Component_Data_URL.CHANNELS.value)
            d_artifact[c.id] = os.path.join(
                c.artifact.url,
                component_msg.Component_Data_URL.ARTIFACTS.value)
        else:
            if c.id in Do_deploytype:
                d_channels[c.id] = os.path.join(
                    c.artifact.url,
                    component_msg.Component_Data_URL.CHANNELS.value)
            d_artifact[c.id] = os.path.join(
                c.artifact.url,
                component_msg.Component_Data_URL.ARTIFACTS.value)
    arguments = arguments + [
        '--d_channels',
        json_utils.simpleDumps(d_channels), '--d_artifact',
        json_utils.simpleDumps(d_artifact)
    ]
    return arguments


def generate_pipeline_id(task_name, model_name) -> str:
    return '.'.join([task_name, model_name])


def create_pipeline_dir(pipeline_dir):
    os.makedirs(pipeline_dir, exist_ok=True)


def db_check_pipeline(task_name, model_name):
    '''通过数据库检查某个pipeline是否存在
    '''
    if db.select(generate_pipeline_id(task_name, model_name)) is None:
        return False
    else:
        return True


def db_update_pipeline(task_name, model_name):
    '''通过数据库插入某个pipeline，以表示其存在
    '''
    db.update('.'.join([task_name, model_name]), 'created')
    if db.select('.'.join([task_name, model_name])) is None:
        return False
    else:
        return True


def db_delete_pipeline(task_name, model_name):
    '''通过数据库删除某个pipeline
    '''
    del db['.'.join([task_name, model_name])]
    if db.select('.'.join([task_name, model_name])) is None:
        return True
    else:
        return False


def db_check_pipeline_component(task_name, model_name, component_id):
    '''通过数据库检查某个pipeline下某个组件是否存在
    '''
    if db.select('.'.join([task_name, model_name, component_id])) is None:
        return False
    else:
        return True


def db_update_pipeline_component(task_name, model_name,
                                 component: base_component.BaseComponent):
    '''通过数据库插入某个pipeline下某个组件，以表示其存在
    '''
    db.update('.'.join([task_name, model_name, component.id]),
              json_utils.componentDumps(component))  # 标记组件被创建
    db.update('.'.join([task_name, model_name, component.id, 'deploytype']),
              component.deploytype)  # 标记组件的deploytype
    db.update('.'.join([task_name, model_name, component.id, 'alias_model']),
              getattr(component, 'alias_model_name', None))  # 标记组件的依赖信息
    # print(getattr(component, 'alias_model_name', None),
    #       getattr(component, 'alias_component_id', None))
    db.update('.'.join(
        [task_name, model_name, component.id, 'alias_component']),
              getattr(component, 'alias_component_id', None))  # 标记组件的依赖信息
    if db.select('.'.join([task_name, model_name, component.id])) is None:
        return False
    else:
        return True


def db_delete_pipeline_component(task_name, model_name,
                                 component: base_component.BaseComponent):
    '''通过数据库删除某个pipeline下某个组件
    '''

    db.delete('.'.join([task_name, model_name, component.id]))
    db.delete('.'.join([task_name, model_name, component.id, 'deploytype']))
    if db.select('.'.join([task_name, model_name, component.id])) is None:
        return True
    else:
        return False


def db_get_pipeline_component_deploytype(task_name, model_name,
                                         alias_component):
    '''通过数据库获取某个pipeline下某个组件的deploytype
    '''
    return db.select('.'.join(
        [task_name, model_name, alias_component, 'deploytype']))


def db_get_pipeline_component_phase(task_name, model_name, component):
    '''通过数据库获取某个pipeline下某个组件的phase
    '''
    return db.select('.'.join([task_name, model_name, component, 'phase']))


def db_reset_pipeline_component_phase(task_name, model_name, component):
    '''通过数据库重置某个pipeline下某个组件的phase
    '''
    db.delete('.'.join([task_name, model_name, component, 'phase']))


def compare_component(task_name, model_name,
                      component: base_component.BaseComponent):
    '''检查组件是否与之前的状态有改变
    '''
    _before = db.select('.'.join([task_name, model_name, component.id]))
    if _before is None:  # 说明之前没有运行过
        component.setChanged(True)
    else:
        _before_component = json_utils.componentLoads(_before)  # 从json里恢复组件
        if cache.judge_update(_before_component, component):
            component.setChanged(True)
        else:
            component.setChanged(False)


def recursive_get_global_component_alias_component(task_name: str,
                                                   model_name: str,
                                                   component_id: str):
    '''找到一个global_component所别名的最原始的那个组件
    '''
    while db.select('.'.join([
            task_name, model_name, component_id, 'alias_model'
    ])) is not None and db.select('.'.join(
        [task_name, model_name, component_id, 'alias_component'])) is not None:
        new_model_name = db.select('.'.join(
            [task_name, model_name, component_id, 'alias_model']))
        new_component_id = db.select('.'.join(
            [task_name, model_name, component_id, 'alias_component']))
        model_name, component_id = new_model_name, new_component_id

    return model_name, component_id


def change_pipeline_phase_to_created(pipeline_id: str):
    '''将pipeline的phase切换至created
    '''
    db.update('.'.join([pipeline_id, 'phase']),
              phases.PIPELINE_PHASES.CREATED.value)


def change_pipeline_phase_to_running(pipeline_id: str):
    '''将pipeline的phase切换至running
    '''
    db.update('.'.join([pipeline_id, 'phase']),
              phases.PIPELINE_PHASES.RUNNING.value)


def change_pipeline_phase_to_finished(pipeline_id: str):
    '''将pipeline的phase切换至finished
    '''
    db.update('.'.join([pipeline_id, 'phase']),
              phases.PIPELINE_PHASES.FINISHED.value)


def change_components_phase_to_created(pipeline_id: str, component_id: str):
    '''将某个组件的状态改变至created
    '''
    db.update('.'.join([pipeline_id, component_id, 'phase']),
              phases.Component_PHASES.CREATED.value)


def change_components_phase_to_running(pipeline_id: str, component_id: str):
    '''将某个组件的状态改变至running
    '''
    db.update('.'.join([pipeline_id, component_id, 'phase']),
              phases.Component_PHASES.RUNNING.value)


def change_components_phase_to_finished(pipeline_id: str, component_id: str):
    '''将某个组件的状态改变至finished
    '''
    db.update('.'.join([pipeline_id, component_id, 'phase']),
              phases.Component_PHASES.FINISHED.value)


def get_global_component_alias_component(
        task_name: str, model_name: str,
        component: global_component.GlobalComponent):
    '''获得global_component的原始model、component
    '''
    alias_model = db.select('.'.join(
        [task_name, model_name, component.id, 'alias_model']))
    alias_component = db.select('.'.join(
        [task_name, model_name, component.id, 'alias_component']))
    return alias_model, alias_component


def get_pipeline_model_component_id(task_name: str, model_name: str):
    return db.select('.'.join([task_name, model_name, 'model_component']))


def delete_pipeline_model_component_id(task_name: str, model_name: str):
    db.delete('.'.join([task_name, model_name, 'model_component']))


def update_pipeline_model_component_id(project_name: str, task_name: str,
                                       model_name: str,
                                       model_component_id: str):
    db.update(
        '.'.join([task_name, model_name, 'model_component']),
        ".".join([project_name, task_name, model_name, model_component_id]))


def update_model_checkpoint(task_name: str, model_name: str, checkpoint: str):
    db.update(".".join([task_name, model_name, 'model_checkpoint']),
              checkpoint)


def get_model_checkpoint(task_name: str, model_name: str):
    return db.select(".".join([task_name, model_name, 'model_checkpoint']))
