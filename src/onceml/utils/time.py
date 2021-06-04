import calendar

import time


def get_timestamp():
    return calendar.timegm(time.gmtime())
