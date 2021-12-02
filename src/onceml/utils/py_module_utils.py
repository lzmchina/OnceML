# -*- encoding: utf-8 -*-
'''
@Description	: 对python模块、对象的一些操作

@Date	:2021/06/18 12:01:23

@Author	:lzm

@version	:0.0.1
'''
def get_func_list_prefix(obj:object,prefix:str):
    '''通过一个字符串前缀，获取所有包含此前缀的方法函数名
    '''
    methodList = []
    for method_name in dir(obj):
        if method_name.lower().startswith(prefix):
            try:
                if callable(getattr(obj, method_name)):
                    methodList.append(str(method_name))
            except:
                methodList.append(str(method_name))
    return methodList
def parse_route(long_str:str,separator:str='_'):
    return '/'+'/'.join(long_str.split('_'))
