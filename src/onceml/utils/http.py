from typing import Tuple
import aiohttp
import asyncio
import json
import onceml.utils.logger as logger
import time
import onceml.types.exception as exception

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


def asyncMsg(hosts: Tuple, data, timeout: int):
    """向hosts列表发送data，如果有失败，则抛出异常
    """
    loop = asyncio.get_event_loop()
    task_list = []
    for host in hosts:
        task_list.append(
            asyncio.ensure_future(
                http_request(host, data, {
                    "Content-Type": "application/json",
                }, 3)))
    #need_again_send = False
    #try:
    results = loop.run_until_complete(asyncio.gather(*task_list))
    logger.logger.info(results)
    for i, host in enumerate(hosts):
        if results[i] != 200:
            #need_again_send = True
            raise exception.SendChannelError
    # except Exception as e:
    #     logger.logger.error(e)
    #     logger.logger.error("发送失败")
    #     need_again_send = True


    # while need_again_send:
    #     time.sleep(2)
    #     need_again_send = False
    #     logger.logger.info("开始重发")
    #     task_list = []
    #     for host in hosts:
    #         # print('2222222')
    #         task_list.append(
    #             asyncio.ensure_future(
    #                 http_request(
    #                     'http://{ip}:{port}'.format(ip=host[0],
    #                                                 port=host[1]), data,
    #                     {
    #                         "Content-Type": "application/json",
    #                     }, timeout)))
    #     try:
    #         results = loop.run_until_complete(asyncio.gather(*task_list))
    #         logger.logger.info(results)
    #         for i, host in enumerate(hosts):
    #             if results[i] != 200:
    #                 need_again_send = True
    #                 break
    #     except:
    #         logger.logger.error("发送失败")
    #         need_again_send = True
def asyncMsgByHost(hosts_list: list, data, timeout: int):
    loop = asyncio.get_event_loop()
    ensure = False
    while not ensure:
        task_list = []
        for host in hosts_list:
            # print('2222222')
            task_list.append(
                asyncio.ensure_future(
                    http_request(host, data, {
                        "Content-Type": "application/json",
                    }, 3)))
        ensure = True
        try:
            results = loop.run_until_complete(asyncio.gather(*task_list))
            logger.logger.info(results)
            for i, host in enumerate(hosts_list):
                if results[i] != 200:
                    ensure = False
                    break
        except:
            logger.logger.error("发送失败")
            ensure = False
