from pathlib import Path
from EdgeGPT import Chatbot as Bing
from typing import Optional
from services import logger
from ..config import config
try:
    import ujson as json
except:
    import json


class Client:
    def __init__(self, cookie_file_path: Optional[Path] = None, proxy: Optional[str] = None):
        self.cookie_file_path = cookie_file_path or config.data_path / 'bing_cookies.json'
        self.proxy = proxy or config.proxy
        self.client = None
        if self.cookie_file_path.exists():
            try:
                self.cookies = json.loads(self.cookie_file_path.read_text())
                self.client = Bing(cookies=self.cookies)
                self.client.proxy = proxy
            except Exception as e:
                logger.error(f"BingGPT客户端初始化失败，错误信息:{e}")

    async def request_api(self, msg: str, reply_mode: str = '') -> str:
        """
        获取bing api 回复
        :param msg: 消息内容
        :param reply_mode: 应答模式
        :return:
        """
        if self.client is None:
            return '管理员没有设置cookie，请求api失败！'
        out = await self.client.ask(msg, conversation_style=reply_mode or config.default_reply_mode)
        return out['item']['messages'][-1]['text']


client = Client()