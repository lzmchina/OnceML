import dbm
import dbm.dumb
import os
import sys
import onceml.global_config as global_config
from onceml.utils.kvdb import DataBase as kvDataBase

_path = os.path.join(os.getcwd(), global_config.OUTPUTSDIR,
                     global_config.database_dir)


def change_path_context(path: str):
    global _path
    _path = os.path.join(path, global_config.OUTPUTSDIR,
                         global_config.database_dir)


def init_db(path: str) -> kvDataBase:
    os.makedirs(path, exist_ok=True)
    return kvDataBase(path)


def close_db(db_connector):
    db_connector.close()


def delete(key):
    db_connector = init_db(_path)
    if db_connector.get(key):
        db_connector.delete(key)


def update(key, value):
    db_connector = init_db(_path)
    if value is None:
        return
    db_connector.update(key, value)


def select(key):
    db_connector = init_db(_path)
    result = None
    if db_connector.get(key):
        result = db_connector.get(key)
    return result
