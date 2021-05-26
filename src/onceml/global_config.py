import os
import os.path as path
from enum import Enum
project_name = 'onceml'
logging_level_env = project_name+'_log'
database_dir = '.db'

PROJECTDIR = os.getcwd()
# 当前运行项目的根目录名
PROJECTDIRNAME = os.path.split(PROJECTDIR)[1]
# 当前运行项目的父路径
PROJECTPARENtDIR = os.path.split(PROJECTDIR)[0]
database_file = path.join(PROJECTDIR, database_dir, '{}.db'.format(project_name))

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