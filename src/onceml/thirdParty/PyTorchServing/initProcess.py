# -*- encoding: utf-8 -*-
'''
@Description	:启动torch serving的进程

@Date	:2022/02/18 15:57:24

@Author	:lzm

@version	:0.0.1
'''
import argparse
import os
import signal
import subprocess
import sys
from onceml.thirdParty.PyTorchServing import TS_PROPERTIES_PATH
from onceml.thirdParty.PyTorchServing.TorchServingUtils import run_ts_serving
ts_process = None  # type:subprocess.Popen


def register():
    # 注册信号处理
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, shutdownHandler)


def shutdownHandler(signalnum, frame):
    print("ctrl +c ")
    if ts_process is not None:
        ts_process.terminate()
        ts_process.wait()
        ts_process.kill()
    sys.exit(0)


def main(args):
    # 启动ts serving进程
    register()
    # 创建工作目录
    os.makedirs(args.model_store,exist_ok=True)
    ts_process = run_ts_serving(
        TS_PROPERTIES_PATH, model_store=os.path.abspath(args.model_store),foreground=True)
    ts_process.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='init torch serving')
    parser.add_argument('--model_store', type=str,
                        help='torch serving的模型目录')

    args = parser.parse_args()
    print(args.model_store)
    main(args=args)
