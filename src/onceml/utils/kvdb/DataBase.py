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
        