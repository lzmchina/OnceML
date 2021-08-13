from typing import Tuple
import aiohttp
import asyncio
import json
import onceml.utils.logger as logger
import time
async def http_request(url, data, headers, timeout):
    async with aiohttp.ClientSession(
            trust_env=True,
            connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with session.post(url,
                                data=json.dumps(data, ensure_ascii=False),
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(timeout)) as res:
            # http://httpbin.org/get?key1=value1&key2=value2
            #print(res.status) res.text()
            await res.text()
            return res.status
def asyncMsg(hosts:Tuple,data,timeout:int):
    loop = asyncio.get_event_loop()
    task_list = []
    
    for host in hosts:
        # print('2222222')
        task_list.append(
            asyncio.ensure_future(
                http_request(
                    host,
                    data, {
                        "Content-Type": "application/json",
                    }, 3)))
    need_again_send = False
    try:
        results = loop.run_until_complete(asyncio.gather(*task_list))
        logger.logger.info(results)
        for i, host in enumerate(hosts):
            if results[i] != 200:
                need_again_send = True
                break
    except:
        logger.logger.error("发送失败")
        need_again_send = True

    while need_again_send:
        time.sleep(2)
        need_again_send = False
        logger.logger.info("开始重发")
        task_list = []
        for host in hosts:
            # print('2222222')
            task_list.append(
                asyncio.ensure_future(
                    http_request(
                        'http://{ip}:{port}'.format(ip=host[0],
                                                    port=host[1]), data,
                        {
                            "Content-Type": "application/json",
                        }, timeout)))
        try:
            results = loop.run_until_complete(asyncio.gather(*task_list))
            logger.logger.info(results)
            for i, host in enumerate(hosts):
                if results[i] != 200:
                    need_again_send = True
                    break
        except:
            logger.logger.error("发送失败")
            need_again_send = True