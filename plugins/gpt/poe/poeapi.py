import asyncio
import threading

import poe
from typing import Optional
from services import logger
from ..config import config


class Client:
    def __init__(self, token: Optional[str] = None, proxy: Optional[str] = None):
        self.token = token or config.poe_token
        self.proxy = proxy or config.proxy
        self.client = None
        if self.token:
            try:
                self.client = poe.Client(token=self.token, proxy=self.proxy)
            except Exception as e:
                logger.error(f"PoeGPT客户端初始化失败，错误信息:{e}")

    async def request_api(self, msg: str, model: str = '', preset: str = '') -> str:
        """
        获取poe api 回复，非阻塞式
        :param msg: 消息内容
        :param model: 模型
        :param preset: 人格
        :return:
        """
        if self.client is None:
            return '管理员没有设置token，请求api失败！'
        clients = self.client.bot_names
        models = {value: key for key, value in clients.items()}
        model = models[model]
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.__request, preset + '\n' + msg, model)
        return result

    def __request(self, msg: str, model: str):
        """
        获取poe api 回复，阻塞式
        :param msg: 消息内容
        :param model: 模型
        :param preset: 人格
        :return:
        """
        for chunk in self.client.send_message(model, msg):
            pass
        out = chunk['text']
        return out


client = Client()