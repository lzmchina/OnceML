import onceml.global_config as global_config

COMPONENT_POD_LABEL = '{}.component.id'.format(
    global_config.project_name).lower()
COMPONENT_POD_LABEL_VALUE='{}.{}.{}.{}'
# 供需要向后续节点发送消息的Cycle类型
COMPONENT_SENDER_POD_LABEL = '{tool}.{{project}}.{{task}}.{{model}}.{{component}}'.format(
    tool=global_config.project_name)
COMPONENT_SENDER_POD_VALUE = '1'