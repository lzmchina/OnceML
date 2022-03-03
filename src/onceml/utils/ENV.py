import os
def get_ENV(key,default=None):
    '''获得某个环境变量的值
    '''
    return os.getenv(key,default=default)