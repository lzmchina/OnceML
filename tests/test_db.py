import dbm
import dbm.dumb

from os import times
import time


def init_db(path: str):
    return dbm.dumb.open(path, 'c')



a = 1
while True:
    print(a)
    db_connector = init_db("test.db")
    db_connector["ta"] = str(a)
    a += 1
    db_connector.close()
    time.sleep(2)
