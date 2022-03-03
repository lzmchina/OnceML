# -*- encoding: utf-8 -*-
'''
@Description	: 对变量的类型以及范围进行判断

@Date	:2022/03/01 17:04:35

@Author	:lzm

@version	:0.0.1
'''
from onceml.types.exception import CustomError

def check_int_of_range(v,left=None,right=None):
    """判断变量v是否是int类型，并且在某个值域里
    """
    assert isinstance(v,int), CustomError("v's type must be int")
    if left is not None:
        assert v>=left,CustomError("v's value must >= {}".format(left))
    if right is not None:
        assert v<=right,CustomError("v's value must <= {}".format(right))
def check_object_not_None(obj):
    """检测对象是否为None
    """
    assert obj is not None, CustomError("obj  must not None")
