import subprocess
import shlex


def outputMar(model_name: str, handler: str, extra_file: str, export_path: str, version: str, archive_format="default") -> bool:
    """将参数配置的mar信息传递给命令行
        1. model-name：模型的名称
        2. extra_file：需要包含的目录或者文件，如果是一个目录，则会自动将里面的文件全部打包进来
        3. handler: model handler的文件路径
        4. export-path:.mar压缩包的导出存放目录
        5. version：为模型指定一个版本，可以为一个时间戳
    """
    args = """
       torch-model-archiver --model-name {} --handler {} --extra-files {} --export-path {} -f --version {} --archive-format {}  
    """.format(model_name, handler, extra_file, export_path, version, archive_format)
    status_code = subprocess.call(shlex.split(args))
    if status_code != 0:
        return False
    return True


def run_ts_serving(ts_config_file: str, model_store: str, foreground: bool = False) -> subprocess.Popen:
    """开启一个子进程，运行torch serving
    1. ts_config_file:torch serving的配置文件路径
    2. model_store:模型
    3. foreground:是否在前端等待
    """
    if foreground:
        foreground = ""
    else:
        foreground = "--foreground"
    process = subprocess.Popen(
        ["torchserve", "--start", "--ncs", foreground, "--ts-config", ts_config_file, "--model-store", model_store], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process
