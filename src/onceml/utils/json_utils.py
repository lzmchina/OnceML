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
        # python基本类型，可以直接序列化
        #return json.JSONEncoder.default(self, obj)
        return super(ComponentEncoder, self).default(obj)
# 将字典转化为组件，loads方法使用


class ComponentDecoder(json.JSONDecoder):
    '''将一个序列化的字典转化为组件
    '''

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):

        def _extract_class(d):
            module_name = d.pop("__module__")
            class_name = d.pop("__class__")
            return getattr(importlib.import_module(module_name), class_name)
        object_type = obj.pop('__object_type__',None)
        # handle your custom classes
        if object_type==_ObjectType.JSONABLE:
            jsonable_class_type = _extract_class(obj)
            if not issubclass(jsonable_class_type, Jsonable):
                raise ValueError('Class %s must be a subclass of Jsonable' %
                                    jsonable_class_type)
            return jsonable_class_type.from_json_dict(obj)
        elif object_type==_ObjectType.CLASS:
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
    return json.dumps(obj)


def componentDumps(obj):
    """Dumps an object to JSON with Jsonable encoding."""
    return json.dumps(obj, cls=ComponentEncoder, sort_keys=True)


def componentLoads(s: str):
    """Loads a JSON into an object with Jsonable decoding."""
    return json.loads(s, default=dict_to_obj)
