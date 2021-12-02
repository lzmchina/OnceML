from enum import Enum
# component数据文件里具体的子目录划分


class Component_Data_URL(Enum):
    STATE = 'state.json'  # 组件状态的文件
    CHANNELS = 'result.json'  # 组件的运行结果，轻量化数据
    ARTIFACTS = 'artifact'  # 组件产生的各种数据文件
