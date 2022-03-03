import onceml.utils.ENV as env_utils
from .configs import INSTANCEID_ENV,IP_ENV
def NameForComponentLeaseName(workflowName:str,podTemplateName:str):
    """获得组件使用的lease资源的名称
    """
    assert isinstance(workflowName,str)
    return "{}.{}".format(workflowName,podTemplateName)
def get_cur_instanceid_ip_from_env():
    """从环境变量里获得当前实例的id以及ip
    """
    return int(env_utils.get_ENV(INSTANCEID_ENV)),env_utils.get_ENV(IP_ENV)
def parse_leader_instanceid_ip_from_env(leader_id:str):
    """从符合leader_election_id_format的字符串中提取出id与ip
    """
    assert isinstance(leader_id,str)
    splits=leader_id.split(":")
    return splits
