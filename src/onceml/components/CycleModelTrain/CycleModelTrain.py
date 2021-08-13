from typing import Dict
from onceml.components.base import BaseComponent, BaseExecutor
from onceml.templates.ModelGenerator import ModelGenerator
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
        

class CycleModelTrain(BaseComponent):
    def __init__(self, model_generator_cls: ModelGenerator, 
                 feauture_component:BaseComponent,
                 emsemble_models:list,
                 max_checkpoint_store=1,
                 **args):
        """
        description
        ---------   
        CycleModelTrain组件是用来产生一个可用于部署的模型，它会提供sample的url list，用户拿到这些路径后，可以自己定义是一起加载到内存里，还是使用队列
        防止占满内存。然后返回一个模型，供后续的model serving使用

        同时，会提供timestamp筛选的功能，只要这些满足条件的samples

        它还拥有模型集成功能，只需要声明依赖的模型的list，就能自动将sample送至依赖的模型，得到结果

       

        Args
        -------
        model_generator_cls:用来封装功能的类

        feauture_component:特征工程组件
        
        emsemble_models:需要集成的模型列表，例如["modelB","modelC"]

        max_checkpoint_store:最多保存模型的数目
        Returns
        -------
        
        Raises
        -------
        
        """

        super().__init__(executor=_executor,
                         inputs=[feauture_component],
                         checkpoint=channel.OutputChannel(str),
                         model_generator_cls=model_generator_cls,
                         emsemble_models=emsemble_models,
                         max_checkpoint_store=max_checkpoint_store,
                         **args)
        self.state = {"file_id": -1}
