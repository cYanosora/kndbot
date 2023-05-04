from revChatGPT.V1 import AsyncChatbot as chatGPT
from typing import Optional, Union, Dict, Any
from services import logger
from ..config import config
try:
    import ujson as json
except:
    import json
promptBase = """
System:$prompt$
---------------
User:"""


class Client:
    def __init__(self, access_token: Optional[str] = None, proxy: Optional[str] = None):
        self.access_token = access_token or config.gpt_token
        self.proxy = proxy or config.proxy
        self.client = None
        if self.access_token:
            try:
                self.client = chatGPT(config={"access_token": self.access_token})
                self.client.config['proxy'] = proxy
            except Exception as e:
                logger.error(f"ChatGPT客户端初始化失败，错误信息:{e}")

    async def request_api(
        self, msg: str, model: str = '', prompt: str = '',
        conversation_id: str = '', parent_id: str = ''
    ) -> Union[str, Dict[str, Any]]:
        """
        获取poe api 回复
        :param msg: 消息内容
        :param model: 模型
        :param prompt: 人格
        :param conversation_id: 消息id
        :param parent_id: 父消息id
        :return:
        """
        if self.client is None:
            return '管理员没有设置token，请求api失败！'
        if prompt:
            msg = promptBase.replace("$prompt$", prompt) + msg
        async for data in self.client.ask(
            msg, model=model, conversation_id=conversation_id, parent_id=parent_id
        ):
            pass
        return data


client = Client()