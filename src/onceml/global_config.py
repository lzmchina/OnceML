import os
import os.path as path
project_name = __package__
logging_level_env = project_name + '_log'
database_dir = '.db'
OUTPUTSDIR = '{}outputs'.format(project_name)  # 输出目录，每个组件的输出会保存在这
PROJECTDIR = os.getcwd()
# 当前运行项目的根目录名
PROJECTDIRNAME = os.path.split(PROJECTDIR)[1]
# 当前运行项目的父路径
# PROJECTPARENtDIR = os.path.split(PROJECTDIR)[0]
database_file = path.join(PROJECTDIR, database_dir,
                          '{}.db'.format(project_name))
SERVERPORT = 10086