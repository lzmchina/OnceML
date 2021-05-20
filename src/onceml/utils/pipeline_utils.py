import onceml.utils.db as db
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
def db_check_pipeline_component(task_name,model_name,component):
    '''通过数据库检查某个pipeline下某个组件是否存在
    '''
    if db.select('.'.join([task_name,model_name,component])) is None:
        return False
    else:
        return True
def db_update_pipeline_component(task_name,model_name,component):
    '''通过数据库插入某个pipeline下某个组件，以表示其存在
    '''
    db.update('.'.join([task_name,model_name,component.id]),'created')#标记组件被创建
    db.update('.'.join([task_name,model_name,component.id,'deploytype']),component.deploytype)#标记组件的deploytype
    if db.select('.'.join([task_name,model_name,component.id])) is None:
        return False
    else:
        return True
def db_get_pipeline_component_deploytype(task_name,model_name,alias_component):
    '''通过数据库获取某个pipeline下某个组件的deploytype
    '''
    return db.select('.'.join([task_name,model_name,alias_component,'deploytype']))

