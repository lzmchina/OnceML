import asyncio
from threading import Thread, Lock
def test_event_loop():
    try:
        #如果是主线程，这里会直接设置新的event_loop
        asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()
asyncio.get_event_loop()
for i in range(5):
    Thread(target=test_event_loop).start()