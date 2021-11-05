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
import onceml.types.channel as channel
from onceml.types.artifact import Artifact
from onceml.utils.time import get_timestamp


class _executor(BaseExecutor):
    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels: Dict[str, channel.Channels] = None,
              input_artifacts: Dict[str, Artifact] = None):
        for key, value in input_channels.items():
            print(key)
            print(value.__dict__)
        print('input_artifacts', input_artifacts)
        for key, value in input_artifacts.items():
            print(key)
            print(value.__dict__)
        file_id = state['file_id']
        todo_files = []
        data_preprocess_dir = list(input_artifacts.values())[0].url
        for file in os.listdir(data_preprocess_dir):
            id = int(os.path.splitext(file)[0])
            if id <= list(
                    input_channels.values())[0]["checkpoint"] and id > file_id:
                # 只有小于等于datasource组件传来的checkpoint、且大于组件状态file_id的文件才会来预处理
                todo_files.append(file)
        # 按照文件的file id排序
        todo_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        print(todo_files)
        if len(todo_files) > 0:
            logger.info("当前有多个文件需要处理")
            gen_id = state['gen_id']
            max_timestamp = 0
            min_timestamp = get_timestamp()
            for file in todo_files:
                logger.info("开始处理{}".format(file))
                object_iter: GeneratorType = self.feature_func(
                    pickle.load(
                        open(os.path.join(data_preprocess_dir, file), 'rb')))

                # 一个文件返回的迭代器，可能会生成多个python object
                # saved_object_space = 10 * 1024 * 1024  #一个文件最小以10MB大小保存
                #objects_list = []
                #current_bytes = 0
                file_id += 1

                for timestamp, x_data, y_label in object_iter:
                    #file_bytes = sys.getsizeof(parse_object)

                    # if current_bytes + file_bytes < saved_object_space:
                    #     objects_list.append(parse_object)
                    #     current_bytes = +file_bytes

                    # else:
                    #     objects_list.append(parse_object)
                    if timestamp is None:
                        timestamp = ''
                    elif type(timestamp) == int:  # timestamp单位建议为秒即可
                        if(timestamp > max_timestamp):
                            max_timestamp = timestamp
                        if(timestamp < min_timestamp):
                            min_timestamp = timestamp
                        timestamp = str(timestamp)
                    else:
                        exception.TypeNotAllowedError("timestamp应该是None或者int")
                    gen_id += 1
                    pickle.dump(
                        (x_data, y_label),
                        open(
                            os.path.join(data_dir,
                                         "{}-{}.pkl".format(timestamp,
                                                            gen_id)), "wb"))
                    # current_bytes = 0
                    # objects_list = []
            state.update({
                "file_id": file_id,
                "gen_id": gen_id,
                "max_timestamp": max_timestamp,
                "min_timestamp": min_timestamp
            })

        else:
            logger.warning("当前没有文件需要处理，跳过")
            return {'checkpoint': state["gen_id"],"max_timestamp":state['max_timestamp'],"min_timestamp":state["min_timestamp"]}
        return {'checkpoint': state["gen_id"],"max_timestamp":state['max_timestamp'],"min_timestamp":state["min_timestamp"]}

    def pre_execute(self, state: State, params: dict, data_dir: str):
        print('this is pre_execute')
        self.feature_func = params['feature_func']


class CycleDataFeaturing(BaseComponent):
    def __init__(self, feature_func: FunctionType,
                 data_preprocess: BaseComponent, **args):
        """
        description
        ---------   
        CycleDataFeaturing组件是在CycleDataPreprocess基础上，对其生成的预处理后的数据进行特征工程，生成samples

        每一条sample可附加时间戳，也可不附加，附加的话，可以在模型训练时附带时间戳的筛选

        Args
        -------
        feature_func：特征工程的处理过程，会传给它预处理后文件的路径，返回可带有时间戳的sample数组或者迭代器
        它应该返回一个list或者迭代器，list的最高维应该是样本数目，每一个元素应该是三元组（timestamp,x_data,y_label）
        把x与y分开是为了模型集成



        Returns
        -------

        Raises
        -------

        """
        if not isinstance(data_preprocess, BaseComponent):
            exception.TypeNotAllowedError("data_preprocess应该是BaseComponent的子类")
        super().__init__(executor=_executor,
                         inputs=[data_preprocess],
                         checkpoint=channel.OutputChannel(int),
                         max_timestamp=channel.OutputChannel(int),
                         min_timestamp=channel.OutputChannel(int),
                         feature_func=feature_func,
                         **args)
        current = get_timestamp()
        self.state = {"file_id": -1, "gen_id": -1,
                      "min_timestamp": current, "max_timestamp": current}
