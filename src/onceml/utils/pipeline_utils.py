import onceml.utils.db as db
import onceml.utils.cache as  cache
import onceml.utils.json_utils as json_utils
import onceml.components.base.base_component as base_component
def db_check_pipeline(task_name,model_name):
    '''通过数据库检查某个pipeline是否存在
    '''
    if db.select('.'.join([task_name,model_name])) is None:
        return False
    else:
        return True
def db_update_pipeline(task_name,model_name):
    '''通过数据库插入某个pipeline，以表示其存在
    '''
    db.update('.'.join([task_name,model_name]),'created')
    if db.select('.'.join([task_name,model_name])) is None:
        return False
    else:
        return True
def db_delete_pipeline(task_name,model_name):
    '''通过数据库删除某个pipeline，以表示其存在
    '''
    del db['.'.join([task_name,model_name])]
    if db.select('.'.join([task_name,model_name])) is None:
        return True
    else:
        return False
def db_check_pipeline_component(task_name,model_name,component_id):
    '''通过数据库检查某个pipeline下某个组件是否存在
    '''
    if db.select('.'.join([task_name,model_name,component_id])) is None:
        return False
    else:
        return True
def db_update_pipeline_component(task_name,model_name,component:base_component.BaseComponent):
    '''通过数据库插入某个pipeline下某个组件，以表示其存在
    '''
    db.update('.'.join([task_name,model_name,component.id]),json_utils.componentDumps(component))#标记组件被创建
    db.update('.'.join([task_name,model_name,component.id,'deploytype']),component.deploytype)#标记组件的deploytype
    if db.select('.'.join([task_name,model_name,component.id])) is None:
        return False
    else:
        return True
def db_delete_pipeline_component(task_name,model_name,component:base_component.BaseComponent):
    '''通过数据库删除某个pipeline下某个组件
    '''
    
    db.delete('.'.join([task_name,model_name,component.id]))
    db.delete('.'.join([task_name,model_name,component.id,'deploytype']))
    if db.select('.'.join([task_name,model_name,component.id])) is None:
        return True
    else:
        return False
def db_get_pipeline_component_deploytype(task_name,model_name,alias_component):
    '''通过数据库获取某个pipeline下某个组件的deploytype
    '''
    return db.select('.'.join([task_name,model_name,alias_component,'deploytype']))
def compare_component(task_name,model_name,component:base_component.BaseComponent):
    '''检查组件是否与之前的状态有改变
    '''
    _before=db.select('.'.join([task_name,model_name,component.id]))
    print(_before)
    if _before is None:#说明之前没有运行过
        component.setChanged(True)
    else:
        _before_component=json_utils.componentLoads(_before)#从json里恢复组件
        if cache.judge_update(_before_component,component):
            component.setChanged(True)
        else:
            component.setChanged(False)