import os
import os.path as path

project_name='onceml'
logging_level_env=project_name+'_log'
database_dir='.db'
database_file=path.join(os.getcwd(),database_dir,'onceml.db')