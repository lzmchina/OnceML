# -*- encoding: utf-8 -*-
'''
@Description	:

@Date	:2021/04/19 15:50:27

@Author	:lzm

@version	:0.0.1
'''
import json
import onceml.components
import importlib
import inspect
import re
from kfp import dsl


class _ObjectType(object):
    """Internal class to hold supported types."""
    # Indicates that the JSON dictionary is an instance of Jsonable type.
    # The dictionary has the states of the object and the object type info is
    # stored as __module__ and __class__ fields.
    JSONABLE = 'jsonable'
    # Indicates that the JSON dictionary is a python class.
    # The class info is stored as __module__ and __class__ fields in the
    # dictionary.
    CLASS = 'class'
    # Indicates that the JSON dictionary is an instance of a proto.Message
    # subclass. The class info of the proto python class is stored as __module__
    # and __class__ fields in the dictionary. The serialized value of the proto is
    # stored in the dictionary with key of _PROTO_VALUE_KEY.
    PROTO = 'proto'
    
    FUNC='function'


class Jsonable():
    """Base class for serializing and deserializing objects to/from JSON.
    The default implementation assumes that the subclass can be restored by
    updating `self.__dict__` without invoking `self.__init__` function.. If the
    subclass cannot hold the assumption, it should
    override `to_json_dict` and `from_json_dict` to customize the implementation.
    """
    def to_json_dict(self):
        """Convert from an object to a JSON serializable dictionary."""
        return self.__dict__

    @classmethod
    def from_json_dict(cls, dict_data):
        """Convert from dictionary data to an object."""
        instance = cls.__new__(cls)
        instance.__dict__ = dict_data
        return instance


# 将组件转化为字典，dumps方法使用
# def replace_placeholder(serialized_component: Text) -> Text:
#     """Replaces the RuntimeParameter placeholders with kfp.dsl.PipelineParam."""
#     placeholders = re.findall(data_types.RUNTIME_PARAMETER_PATTERN,
#                             serialized_component)

#     for placeholder in placeholders:
#         # We need to keep the level of escaping of original RuntimeParameter
#         # placeholder. This can be done by probing the pair of quotes around
#         # literal 'RuntimeParameter'.
#         placeholder = fix_brackets(placeholder)
#         cleaned_placeholder = placeholder.replace('\\', '')  # Clean escapes.
#         parameter = json_utils.loads(cleaned_placeholder)
#         dsl_parameter_str = str(dsl.PipelineParam(name=parameter.name))

#         serialized_component = serialized_component.replace(placeholder,
#                                                             dsl_parameter_str)

#     return serialized_component


# def fix_brackets(placeholder: Text) -> Text:
#     """Fix the imbalanced brackets in placeholder.
#     When ptype is not null, regex matching might grab a placeholder with }
#     missing. This function fix the missing bracket.
#     Args:
#     placeholder: string placeholder of RuntimeParameter
#     Returns:
#     Placeholder with re-balanced brackets.
#     Raises:
#     RuntimeError: if left brackets are less than right brackets.
#     """
#     lcount = placeholder.count('{')
#     rcount = placeholder.count('}')
#     if lcount < rcount:
#         raise RuntimeError(
#         'Unexpected redundant left brackets found in {}'.format(placeholder))
#     else:
#         patch = ''.join(['}'] * (lcount - rcount))
#     return placeholder + patch
def fix_brackets(jsonstr: str) -> str:
    pass


class ComponentEncoder(json.JSONEncoder):
    '''将一个component序列化
    '''

    # def encode(self, obj:object) :
    #     """Override encode to prevent redundant dumping."""
    #     print('ComponentEncoder encode()')
    #     if isinstance(obj,Jsonable):
    #         return self.default(obj)
    #     #基本类型
    #     return super(ComponentEncoder, self).encode(obj)

    def default(self, obj: object):
        #print('ComponentEncoder default():',obj)
        if isinstance(obj, Jsonable):
            #print('ComponentEncoder default() Jsonable')
            d = {}
            d['__class__'] = obj.__class__.__name__
            d['__module__'] = obj.__class__.__module__
            d['__object_type__'] = _ObjectType.JSONABLE
            d.update(obj.to_json_dict())
            return d
        elif inspect.isclass(obj):
            #一般的class
            #print('ComponentEncoder default() class')
            d = {}
            d['__class__'] = obj.__name__
            d['__module__'] = obj.__module__
            d['__object_type__'] = _ObjectType.CLASS
            return d
        elif inspect.isfunction(obj):
            #一般的function
            d = {}
            d['__class__'] = obj.__name__
            d['__module__'] = obj.__module__
            d['__object_type__'] = _ObjectType.FUNC
            return d
        # python基本类型，可以直接序列化
        #return json.JSONEncoder.default(self, obj)
        return super(ComponentEncoder, self).default(obj)


# 将字典转化为组件，loads方法使用


class ComponentDecoder(json.JSONDecoder):
    '''将一个序列化的字典转化为组件
    '''
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self,
                                  object_hook=self.object_hook,
                                  *args,
                                  **kwargs)

    def object_hook(self, obj):
        if '__object_type__' not in obj:
            return obj

        def _extract_class(d):
            module_name = d.pop("__module__")
            class_name = d.pop("__class__")
            return getattr(importlib.import_module(module_name), class_name)

        object_type = obj.pop('__object_type__', None)
        # handle your custom classes
        if object_type == _ObjectType.JSONABLE:
            jsonable_class_type = _extract_class(obj)
            if not issubclass(jsonable_class_type, Jsonable):
                raise ValueError('Class %s must be a subclass of Jsonable' %
                                 jsonable_class_type)
            return jsonable_class_type.from_json_dict(obj)
        elif object_type == _ObjectType.CLASS:
            return _extract_class(obj)
        elif object_type==_ObjectType.FUNC:
            return _extract_class(obj)
        # handling the resolution of nested objects
        if isinstance(obj, dict):
            for key in list(obj):
                obj[key] = self.object_hook(obj[key])
            return obj
        if isinstance(obj, list):
            for i in range(0, len(obj)):
                obj[i] = self.object_hook(obj[i])
            return obj
        return obj


def obj_to_dict(obj):
    d = {}
    d['__class__'] = obj.__class__.__name__
    d['__module__'] = obj.__module__
    d.update(obj.__dict__)
    return d


# 将字典转化为自定义的类，loads方法使用


def dict_to_obj(d):
    if '__class__' in d:
        class_name = d.pop('__class__')
        module_name = d.pop('__module__')
        module = __import__(module_name)
        class_ = getattr(module, class_name)
        args = dict((key.encode('ascii'), value) for key, value in d.items())
        instance = class_(**args)
    else:
        instance = d
    return instance


def simpleLoads(jsonstr: str):
    return json.loads(jsonstr)


def simpleDumps(obj: object):
    return json.dumps(obj, sort_keys=True)


def componentDumps(obj):
    """Dumps an object to JSON with Jsonable encoding."""
    return json.dumps(obj, cls=ComponentEncoder, sort_keys=True)


def componentLoads(s: str):
    """Loads a JSON into an object with Jsonable decoding."""
    return json.loads(s, cls=ComponentDecoder)

def objectDumps(obj):
    """Dumps an object to JSON with Jsonable encoding."""
    return componentDumps(obj=obj)


def objectLoads(s: str):
    """Loads a JSON into an object with Jsonable decoding."""
    return componentLoads(s)