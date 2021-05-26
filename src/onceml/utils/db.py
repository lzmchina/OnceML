import dbm
import os
import sys
import onceml.global_config as global_config


os.makedirs(os.path.join(os.getcwd(), global_config.database_dir),exist_ok=True)
def init_db(path:str):
    return dbm.open(path, 'c')
db_connector=init_db(global_config.database_file)
def close_db(db_connector):
    db_connector.close()

def delete(key):
    if db_connector.get(key):
        del db_connector[key]

def update(key,value):
    if value is None:
        return
    db_connector[key] = value

def select(key):
    if db_connector.get(key):
        return db_connector[key]
    else:
        return None

def allKeys():
    return db_connector.keys() 