import onceml.global_config as global_config
PORT = 4040
# 获得当前leader
LEADERURL = "/"
leader_election_id_format = "$({INSTANCE_ID}):$({POD_IP})"

IP_ENV = "{}_IP".format(global_config.project_name.upper())
INSTANCEID_ENV = "{}_INSTANCE_ID".format(global_config.project_name.upper())
NAMESPACE_ENV = "{}_NAMESPACE".format(global_config.project_name.upper())
REPLICAS_ENV = "{}_REPLICAS".format(global_config.project_name.upper())
IMAGE = "registry.cn-hangzhou.aliyuncs.com/liziming/leaderelection:0.0.1"
