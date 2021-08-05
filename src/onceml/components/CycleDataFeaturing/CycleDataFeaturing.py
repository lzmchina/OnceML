from typing import Dict
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.types.state import State
import time
import os
import re
from onceml.utils.logger import logger
import shutil
from types import FunctionType, GeneratorType
import sys
import pickle
import onceml.types.exception as exception

class _executor(BaseExecutor):
    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels: Dict[str, Dict] = None,
              input_artifacts: Dict[str, str] = None):
        for key, value in input_channels.items():
            print(key)
            print(value.__dict__)
        print('input_artifacts', input_artifacts)
        for key, value in input_artifacts.items():
            print(key)
            print(value.__dict__)
        file_id = state['fileid']
        todo_files = []
        for file in os.listdir(input_artifacts.values()[0]):
            id = int(os.path.splitext(file)[0])
            if id <= input_channels.values()[0]["checkpoint"] and id > file_id:
                #只有小于等于datasource组件传来的checkpoint、且大于组件状态file_id的文件才会来预处理
                todo_files.append(file)
        #按照文件的file id排序
        todo_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        print(todo_files)
        if len(todo_files) > 0:
            logger.info("当前有多个文件需要处理")
            logger.info("开始处理{}".format(todo_files[0]))
            object_iter: GeneratorType = self.feature_func(
                os.path.join(input_artifacts.values()[0], todo_files[0]))

            #一个文件返回的迭代器，可能会生成多个python object
            #saved_object_space = 10 * 1024 * 1024  #一个文件最小以10MB大小保存
            #objects_list = []
            #current_bytes = 0
            gen_id = state['gen_id']
            for timestamp,parse_object in object_iter:
                #file_bytes = sys.getsizeof(parse_object)

                # if current_bytes + file_bytes < saved_object_space:
                #     objects_list.append(parse_object)
                #     current_bytes = +file_bytes

                # else:
                #     objects_list.append(parse_object)
                if timestamp is None :
                    timestamp=''
                elif type(timestamp)==int:# timestamp单位建议为秒即可
                    timestamp=str(timestamp)
                else:
                    exception.TypeNotAllowedError("timestamp应该是None或者int")
                gen_id += 1
                pickle.dump(
                    parse_object,
                    os.path.join(data_dir, "{}-{}.pkl".format(timestamp,gen_id)))
                    # current_bytes = 0
                    # objects_list = []
            state.update({
                "fileid": int(os.path.splitext(todo_files[0])[0]),
                "gen_id": gen_id
            })

        else:
            logger.warning("当前没有文件需要处理，跳过")
        return {'checkpoint': state["gen_id"]}

    def pre_execute(self, state: State, params: dict, data_dir: str):
        print('this is pre_execute')
        self.feature_func = params['feature_func']


class CycleDataFeaturing(BaseComponent):
    def __init__(self, feature_func: FunctionType, **args):
        """
        description
        ---------   
        CycleDataFeaturing组件是在CycleDataPreprocess基础上，对其生成的预处理后的数据进行特征工程，生成samples

        每一条sample可附加时间戳，也可不附加，附加的话，可以在模型训练时附带时间戳的筛选

        Args
        -------
        feature_func：特征工程的处理过程，会传给它预处理后文件的路径，返回可带🈶️时间戳的sample数组或者迭代器


        Returns
        -------
        
        Raises
        -------
        
        """

        super().__init__(executor=_executor,
                         inputs=None,
                         checkpoint=channel.OutputChannel(str),
                         feature_func=feature_func,
                         **args)
        self.state = {"file_id": -1, "gen_id": -1}
