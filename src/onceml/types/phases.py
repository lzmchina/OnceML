from enum import Enum


# pipeline阶段
class PIPELINE_PHASES(Enum):
    CREATED = 'created'
    RUNNING = 'running'
    FINISHED = 'finished'


# component阶段
class Component_PHASES(Enum):
    CREATED = 'created'
    RUNNING = 'running'
    FINISHED = 'finished'
