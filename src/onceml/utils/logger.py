import logging
import os
import onceml.global_config as global_config
from colorlog import ColoredFormatter

__logging_level = os.getenv(global_config.logging_level_env, 'INFO')

logger = logging.getLogger(global_config.project_name)
logger.setLevel(__logging_level)
__handler = logging.StreamHandler()
# __formatter = logging.Formatter(fmt='%(levelname)8s : %(name)8s : %(asctime)s : %(created).0f : %(message)s',
#                                 datefmt='%Y-%m-%d %H:%M:%S'
#                                 )
LOGFORMAT = "%(log_color)s %(levelname)8s : %(name)8s : %(asctime)s : %(created).0f : %(message)s %(reset)s"
formatter = ColoredFormatter(fmt=LOGFORMAT,datefmt='%Y-%m-%d %H:%M:%S')
__handler.setFormatter(formatter)
logger.addHandler(__handler)
