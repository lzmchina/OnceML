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
from onceml.types.channel import Channels
from onceml.types.artifact import Artifact
class _executor(BaseExecutor):
    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels: Dict[str, Channels] = None,
              input_artifacts: Dict[str, Artifact] = None):
        for key, value in input_channels.items():
            print(key)
            print(value.__dict__)
        print('input_artifacts', input_artifacts)
        for key, value in input_artifacts.items():
            print(key)
            print(value.__dict__)
        file_id = state['fileid']
        todo_files = []
        data_source_dir=list(input_artifacts.values())[0].url
        for file in os.listdir(data_source_dir):
            id = int(os.path.splitext(file)[0])
            if id <= list(input_channels.values())[0]["checkpoint"] and id > file_id:
                #只有小于等于datasource组件传来的checkpoint、且大于组件状态file_id的文件才会来预处理
                todo_files.append(file)
        #按照文件的file id排序
        todo_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        print(todo_files)
        if len(todo_files) > 0:
            logger.info("当前有多个文件需要处理")
            for file in todo_files:
                if int(os.path.splitext(file)[0])!=file_id+1:
                    logger.error("CycleDataPreprocess与上游组件CycleDataSource的状态不一致")
                    sys.exit(1)
                logger.info("开始处理{}".format(file))
                file_object = self.read_file_func(
                    os.path.join(data_source_dir, file))
                #一个文件返回的迭代器，可能会生成多个python object
                # saved_object_space = 10 * 1024 * 1024  #一个文件最小以10MB大小保存
                # objects_list = []
                # current_bytes = 0
                #gen_id = state['gen_id']
                #for parse_object in object_iter:
                    # file_bytes = sys.getsizeof(parse_object)

                    # if current_bytes + file_bytes < saved_object_space:
                    #     objects_list.append(parse_object)
                    #     current_bytes = +file_bytes

                    # else:
                    #     objects_list.append(parse_object)
                    #gen_id += 1\
                file_id+=1
                pickle.dump(file_object,
                            open(os.path.join(data_dir, "{}.pkl".format(file_id)),"wb"))
                    # current_bytes = 0
                    # objects_list = []
            state.update({
                "fileid": file_id,
            })

        else:
            logger.warning("当前没有文件需要处理，跳过")
            return  {'checkpoint': state["fileid"]}
        return {'checkpoint': state["fileid"]}

    def pre_execute(self, state: State, params: dict, data_dir: str):
        print('this is pre_execute')
        self.read_file_func = params['file_parse_func']
        #创建一个文件夹，放入用户需要的其他文件
        #os.makedirs(os.path.join(data_dir, "extras"),exist_ok=True)

class CycleDataPreprocess(BaseComponent):
    def __init__(self, file_parse_func: FunctionType, data_source:BaseComponent,parallel=1,**args):
        """
        description
        ---------
        CycleDataPreprocess是用来进行数据预处理的，收到CycleDataSource的checkpoint后，会解析文件，并将结果保存为pickle对象

        Args
        -------
        file_parse_func:解析文件的函数，需要用户自己提供，会给定一个文件的url，有用户自己定义怎样解析，怎样预处理
        用户需要在这个函数里返回一个python对象，组件再调用这个迭代器，去生成python对象数组，最后保存成二进制文件

        parallel:组件的并行度

        Returns
        -------
        
        Raises
        -------
        
        """
        if  (not isinstance(data_source,BaseComponent)):
            exception.TypeNotAllowedError("data_source应该是BaseComponent的子类")
        super().__init__(file_parse_func=file_parse_func,
                         executor=_executor(parallel),
                         inputs=[data_source],
                         checkpoint=channel.OutputChannel(int),
                         **args)
        self.state = {
            "fileid": -1,  #fileid表示对上一组件的输出文件的处理进度
        }
