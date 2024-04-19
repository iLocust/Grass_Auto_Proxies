import asyncio
import random
import ssl
import json
import time
import uuid
import requests
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
import os
from dotenv import load_dotenv

load_dotenv()

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {"User-Agent": random_user_agent}
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "3.3.2"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(socks5_proxy)

async def main():
    while True:
        user_id = os.getenv('USER_ID')
        user_id = 'dfcd1680-354d-4886-af0f-96caef904c93'  # Static user ID
        url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
        response = requests.get(url)
        socks5_proxy_list = response.text.splitlines() if response.status_code == 200 else []
        
        tasks = [asyncio.ensure_future(connect_to_wss(i, user_id)) for i in socks5_proxy_list]
        await asyncio.gather(*tasks)

        await asyncio.sleep(24 * 3600)  # Wait for 24 hours before restarting

if __name__ == '__main__':
    asyncio.run(main())
