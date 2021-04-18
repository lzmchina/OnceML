class Pipline():
    '''
    Pipline的逻辑：

    一个pipline可以看作是多个组件component的组成，比如从数据源、数据预处理、……最后到模型发布

    而且一个pipline要做到模型分离，对于同一个场景，使用的数据相同，而模型不同，所以需要做到模型的训练分离
    '''
    def __init__(self,pipeline_name,model_name,components):
        super().__init__()