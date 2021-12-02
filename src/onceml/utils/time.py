import calendar

import time


def get_timestamp():
    '''获得一个秒的时间戳
    '''
    return calendar.timegm(time.gmtime())
