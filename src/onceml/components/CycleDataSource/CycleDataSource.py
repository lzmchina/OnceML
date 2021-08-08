from onceml.components.base import BaseComponent, BaseExecutor
from onceml.types.state import State
import os
import re
from onceml.utils.logger import logger
import shutil
import onceml.types.channel as channel


class _executor(BaseExecutor):
    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels=None,
              input_artifacts=None):

        batch_dirs = []
        for file in os.listdir(params['listen_data_dir']):
            if os.path.isdir(
                    os.path.join(params['listen_data_dir'],
                                 file)) and self.file_name_pattern.match(file):
                #如果是batch-{}模式，且是文件夹，则进行相应的处理
                id = int(file.split("-")[1])
                if id > state["currentId"]:
                    batch_dirs.append(id)
        batch_dirs.sort()
        print(batch_dirs)
        if len(batch_dirs) > 1:
            logger.info("当前有多个目录")
            logger.info("开始处理{}".format(batch_dirs[0]))
            file_id = state["fileid"]
            for file in os.listdir(
                    os.path.join(params['listen_data_dir'],
                                 "batch-{}".format(batch_dirs[0]))):
                file_id += 1
                shutil.copyfile(
                    os.path.join(params['listen_data_dir'],
                                 "batch-{}".format(batch_dirs[0]), file),
                    os.path.join(
                        data_dir, "{}{}".format(file_id,
                                                os.path.splitext(file)[-1])))
            state.update({"fileid": file_id, "currentId": batch_dirs[0]})

        else:
            logger.warning("当前只有一个符合条件的目录，跳过")
            return None
        return {'checkpoint': state["fileid"]}

    def pre_execute(self, state: State, params: dict, data_dir: str):
        print('this is pre_execute')
        self.file_name_pattern = re.compile("^batch-\d+$")
        #创建一个文件夹，放入用户需要的其他文件
        # os.makedirs(os.path.join(data_dir, "extras"),exist_ok=True)
        


class CycleDataSource(BaseComponent):
    def __init__(self, listen_data_dir: str, **args):
        """
        description
        ---------
        CycleDataSource是充当数据源的角色，可以监听某个文件夹下的数据变动，从而向后传播信息，驱动后续组件执行

        CycleDataSource会在listen_data_dir下匹配batch-{d},从batch-0开始，处理完里面的数据后，如果出现了batch-1目录，就不会再处理batch-0了，认为
        batch-0里面的文件已经处理完成

        这里设想的是当出现batch-1目录，batch-0目录可以认为不会再有变动，然后就可以对batch-0目录里的文件进行

        但是用户可能会用到其他的静态文件，不是数据集里的一部分
        Args
        -------
        listen_data_dir:监听的目录（由于运行在容器里，这个目录必须是容器内可访问的，因此应当为project下的子目录，因为project被挂载到容器里了）

        Returns
        -------
        
        Raises
        -------
        
        """

        super().__init__(listen_data_dir=listen_data_dir,
                         executor=_executor,
                         inputs=None,
                         checkpoint=channel.OutputChannel(str),
                         **args)
        self.state = {
            "currentId": -1,  # 当前正在处理的文件夹id，从-1开始,表示还没有开始处理
            "fileid": -1
        }