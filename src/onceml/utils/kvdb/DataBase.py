import os
import fcntl
import onceml.utils.logger as logger
class DataBase():
    """以文件存储的简易key-value数据库
    """
    def __init__(self,dir:str) -> None:
        """
        description
        ---------
        
        Args
        -------
        dir: 数据的存储目录
        
        Returns
        -------
        
        Raises
        -------
        
        """
        self.dataDir=dir
    def update(self,key:str,value:str):
        '''
        '''
        if key is None or not isinstance(key,str) or len(key)==0:
            raise Exception("key必须是长度不为0的字符串")
        with open(os.path.join(self.dataDir,key),"w") as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            f.write(value)
    def delete(self,key:str):
        if key is None or not isinstance(key,str) or len(key)==0:
            raise Exception("key必须是长度不为0的字符串")
        if os.path.exists(os.path.join(self.dataDir,key)):
            try:
                os.remove(os.path.join(self.dataDir,key))
            except:
                logger.logger.error("key ：{}已经不存在了".format(key))
    def get(self,key:str):
        if key is None or not isinstance(key,str) or len(key)==0:
            raise Exception("key必须是长度不为0的字符串")
        if os.path.exists(os.path.join(self.dataDir,key)):
            try:
                with open(os.path.join(self.dataDir,key),"r") as f:
                    fcntl.flock(f,fcntl.LOCK_EX)
                    return f.readline()
            except:
                logger.logger.error("key ：{}已经不存在了".format(key))
                return None
        else:
            return None