from onceml.components.base import BaseComponent, BaseExecutor
from onceml.types.state import State


class _executor(BaseExecutor):
    def Cycle(self,
              state: State,
              params: dict,
              data_dir: str,
              input_channels=None,
              input_artifacts=None):
        print('current component:', self.__class__)
        print('params', params)
        print('state', state)
        print('input_channels', input_channels)
        print('input_artifacts', input_artifacts)
        for key, value in input_channels.items():
            print(key)
            print(value.__dict__)
        print('input_artifacts', input_artifacts)
        for key, value in input_artifacts.items():
            print(key)
            print(value.__dict__)
        time.sleep(60)
        return {'resulta': 'fdfdf', 'resultb': 25}

    def pre_execute(self, state: State):
        print('this is pre_execute')


class CycleDataSource(BaseComponent):
    def __init__(self, listen_data_dir: str, str, **args):
        """
        description
        ---------
        CycleDataSource是充当数据源的角色，可以监听某个文件夹下的数据变动，从而向后传播信息，驱动后续组件执行

        CycleDataSource会在listen_data_dir下匹配datano{d},从datano0开始，处理完里面的数据后，如果出现了datano1目录，就不会再处理datano0了，认为
        datano0里面的文件已经处理完成
        Args
        -------
        listen_data_dir:监听的目录（由于运行在容器里，这个目录必须是容器内可访问的，因此应当为project下的子目录，因为project被挂载到容器里了）

        Returns
        -------
        
        Raises
        -------
        
        """

        super().__init__(executor=_executor, inputs=None, **args)