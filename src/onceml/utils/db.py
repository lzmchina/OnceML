import dbm
import dbm.dumb
import os
import sys
import onceml.global_config as global_config

_path = os.path.join(os.getcwd(), global_config.OUTPUTSDIR,
                     global_config.database_dir)
os.makedirs(_path, exist_ok=True)


def init_db(path: str):
    return dbm.dumb.open(path, 'c')


def close_db(db_connector):
    db_connector.close()


def delete(key):
    db_connector = init_db(global_config.database_file)
    if db_connector.get(key):
        del db_connector[key]
        db_connector.sync()
    close_db(db_connector)


def update(key, value):
    db_connector = init_db(global_config.database_file)
    if value is None:
        return
    db_connector[key] = value
    close_db(db_connector)


def select(key):
    db_connector = init_db(global_config.database_file)
    result = None
    if db_connector.get(key):
        result = db_connector[key].decode('utf-8')
    close_db(db_connector)
    return result
