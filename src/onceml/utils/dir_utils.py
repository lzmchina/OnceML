import os
import re

def getLatestTimestampDir(parentDir: str)->int:
    '''返回模型checkpoint目录下最新的checkpoint目录
    
    '''
    timestamp = []
    for dir in os.listdir(parentDir):
        if os.path.isdir(os.path.join(parentDir, dir)):
            timestamp.append(int(dir))
    timestamp.sort()
    if len(timestamp)>0:
        return timestamp[-1]
    else:
        return None
