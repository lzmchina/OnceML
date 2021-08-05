from typing import Any, Dict
import json
from onceml.utils.json_utils import  Jsonable

class State(Jsonable):
    """组件的状态
    description
    ---------
    组件的状态需要做到保存，每次开发者修改状态，都能及时作出保存
    """
    def __init__(self,
                 data: Dict[str, Any] = None,
                 json_path: str = None) -> None:
        """State类型
        description
        ---------
        
        Args
        -------
        json_path：保存state的json路径
        Returns
        -------
        
        Raises
        -------
        
        """
        self.json_url = json_path
        self.data = data or {}
    def to_json_dict(self):
        return self.__dict__
    def load(self, json_url: str=None):
        '''从一个json文件里恢复state
        '''
        self.data = json.load(open(json_url or self.json_url, 'r'))

    def dump(self, json_url: str=None):
        '''将state保存到json文件里
        '''
        json.dump(self.data, open( json_url or self.json_url,'w'),indent=4)

    def __getitem__(self, key):
        return self.data.get(key)
    def __setitem__(self,key,value):
        self.data.update({key:value})
        self.dump()
    def update(self,data:Dict[str,Any]):
        self.data.update(data)
        self.dump()
    def __str__(self) -> str:
        return self.data.__str__()
