from typing import Dict, List, Tuple
import aiohttp
import asyncio
import json
import onceml.utils.logger as logger
import time
import onceml.types.exception as exception
import gc
import requests

async def http_request(url, data, headers, timeout) -> Tuple[int, Dict]:
    async with aiohttp.ClientSession(
            trust_env=True,
            connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with session.post(url,
                                data=json.dumps(data, ensure_ascii=False),
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(timeout)) as res:
            # http://httpbin.org/get?key1=value1&key2=value2
            # print(res.status) res.text()
            json_body = await res.json()
            return res.status, json_body
async def http_request_raw(url, data, headers, timeout) -> Tuple[int, Dict]:
    async with aiohttp.ClientSession(
            trust_env=True,
            connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with session.post(url,
                                data=json.dumps(data, ensure_ascii=False),
                                headers=headers,
                                timeout=aiohttp.ClientTimeout(timeout)) as res:
            # http://httpbin.org/get?key1=value1&key2=value2
            # print(res.status) res.text()
            body = await res.text()
            return res.status, body

async def http_request_get(url, headers, timeout):
    async with aiohttp.ClientSession(
            trust_env=True,
            connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with session.get(url,
                               headers=headers,
                               timeout=aiohttp.ClientTimeout(timeout)) as res:
            # http://httpbin.org/get?key1=value1&key2=value2
            # print(res.status) res.text()
            json_body = await res.json()
            return res.status, json_body


def asyncMsg(hosts: Tuple, data, timeout: int = 3, auto_check_ok=True,auto_json=True):
    """向hosts列表发送data，如果有失败，则抛出异常

    """

    try:
        # 如果是主线程，这里会直接设置新的event_loop
        asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()
    # logger.logger.info('Before gc:{}'.format(
    #     len(asyncio.Task.all_tasks(loop=loop))))

    # gc.collect()

    # logger.logger.info('After gc:{}'.format(
    #     len(asyncio.Task.all_tasks(loop=loop))))
    logger.logger.info(hosts)
    task_list = []
    if auto_json:
        for host in hosts:
            task_list.append(
                asyncio.ensure_future(
                    http_request(host, data, {
                        "Content-Type": "application/json",
                    }, 3)))
    else:
        for host in hosts:
            task_list.append(
                asyncio.ensure_future(
                    http_request_raw(host, data, {
                        "Content-Type": "application/json",
                    }, 3)))
    #need_again_send = False
    # try:
    results = loop.run_until_complete(asyncio.gather(
        *task_list))  # type:List[Tuple[int,Dict]]
    logger.logger.info(results)
    if auto_check_ok:
        for i, host in enumerate(hosts):
            if results[i][0] != 200:
                #need_again_send = True
                raise exception.SendChannelError
    else:
        return results


def asyncMsgGet(hosts: Tuple, timeout: int = 3, auto_check_ok=True):
    """向hosts列表发送data，如果有失败，则抛出异常

    """

    try:
        # 如果是主线程，这里会直接设置新的event_loop
        asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()
    # logger.logger.info('Before gc:{}'.format(
    #     len(asyncio.Task.all_tasks(loop=loop))))

    # gc.collect()

    # logger.logger.info('After gc:{}'.format(
    #     len(asyncio.Task.all_tasks(loop=loop))))
    logger.logger.info(hosts)
    task_list = []
    for host in hosts:
        task_list.append(
            asyncio.ensure_future(
                http_request_get(host, {}, 3)))

    results = loop.run_until_complete(asyncio.gather(*task_list))
    logger.logger.info(results)
    if auto_check_ok:
        for i, host in enumerate(hosts):
            if results[i][0] != 200:
                #need_again_send = True
                raise exception.SendChannelError
    else:
        return results
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
def syncGet(url,headers=None,params=None):
    """同步的http Get请求
    description
    ---------
    
    Args
    -------
    
    Returns
    -------
    
    Raises
    -------
    
    """
    return requests.get(url=url,headers=headers,params=params)
def syncPost(url,headers=None,data=None,timeout=3):
    """同步的http Post请求
    description
    ---------
    
    Args
    -------
    
    Returns
    -------
    
    Raises
    -------
    
    """
    return requests.post(url=url,headers=headers,json=data,timeout=timeout)