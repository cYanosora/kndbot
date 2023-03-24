import time
from pathlib import Path
from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field, root_validator
from services import logger
from .openai import request_api
from .config import config as _config, ai_preset, knd_preset
try:
    import ujson as json
except ModuleNotFoundError:
    import json


class Session:
    """ 存储个体正在进行的会话 """
    chat_count: int = 1  # 此个体当天已对话次数
    last_timestamp: int = 0  # 此个体上次对话时间

    def __init__(self, _id: str):
        """ 使用id标识每个个体的会话信息 """
        self.session_id = _id
        self.preset = _config.gpt3_default_preset
        self.conversation = []
        self.reset()
        self.token_record = []
        self.total_tokens = 0

    def reset(self):
        """ 重置会话 """
        self.conversation = []

    def reset_preset(self):
        """ 重置人格为默认人格 """
        self.preset = _config.gpt3_default_preset

    def set_preset(self, msg: str) -> str:
        """ 设置人格，会重置会话 """
        msg = msg.strip().lower()
        if msg in ['默认', 'ai助手']:
            self.preset = ai_preset
        elif msg in ["奏宝", "knd", "kanade", "小奏", "宵崎奏", "奏"]:
            self.preset = knd_preset
        else:
            self.preset = msg.strip()
        self.reset()
        return self.preset

    def load_user_session(self, session_name: str, session_owner: str) -> str:
        """ 导入用户会话 """
        for session in setting.session:
            if session['name'] == session_name and session['owner'] == session_owner:
                msg_config = session['data']
                self.set_preset(msg_config[0]['content'])
                self.conversation = msg_config[1:]
                return f'成功导入会话: {session_name}\n' \
                       f'共{len(self.conversation)}条对话'
        else:
            return ''

    def dump_user_session(self, session_name: str, session_owner: str):
        """ 导出用户会话 """
        setting.session.append({
            "owner": session_owner,
            "name": session_name,
            "data": [{"role": "system", "content": self.preset}] + self.conversation
        })
        setting.save()
        return f'成功导出会话: {session_name}\n' \
               f'共{len(self.conversation)}条对话'

    async def get_chat_response(self, msg, is_admin) -> Union[bool, str]:
        """ chat api会话 """
        if _config.openai_api_key == '':
            return f'无API Keys，请在配置文件或者环境变量中配置'

        # 全局检查当天使用次数
        def check_and_reset() -> bool:
            if is_admin:
                return False
            # 超过一天重置
            from datetime import datetime
            last = datetime.fromtimestamp(self.last_timestamp)
            now = datetime.fromtimestamp(time.time())
            delta = now - last
            if delta.days > 0:
                self.chat_count = 0

            # 一天之内检查次数
            if self.chat_count >= _config.gpt3_chat_count_per_day:
                return True
            return False

        if check_and_reset():
            return f'今日聊天次数达到上限，请明天再来~'

        import tiktoken
        encoding = tiktoken.encoding_for_model(_config.gpt3_model)
        # 长度超过4096时，删除最早的一次会话
        while self.total_tokens + len(encoding.encode(msg)) > 4096 - _config.gpt3_max_tokens:
            logger.debug(f"长度超过{4096 - _config.gpt3_max_tokens}，删除最早的一次会话")
            self.total_tokens -= self.token_record[0]
            del self.conversation[0]
            del self.token_record[0]

        res, ok = await request_api(
            _config.gpt3_proxy, _config.openai_api_key, self.preset, self.conversation, msg
        )
        if ok:
            self.chat_count += 1
            self.last_timestamp = int(time.time())
            # 输入token数
            self.token_record.append(res['usage']['prompt_tokens'] - self.total_tokens)
            # 回答token数
            self.token_record.append(res['usage']['completion_tokens'])
            # 总token数
            self.total_tokens = res['usage']['total_tokens']

            logger.debug(res['usage'])
            logger.debug(self.token_record)
            return self.conversation[-1]['content']
        else:
            # 出现错误自动重置
            self.reset()
            return res


class Setting(BaseModel):
    session: List[Dict[str, Any]] = Field(default_factory=list)
    preset: Dict[str, str] = Field(default_factory=dict)
    config: Dict[str, Any] = {
        'chatmode': _config.gpt3_chat_mode,
        'model': _config.gpt3_model,
        'send_image': _config.gpt3_image_render,
        'token': _config.openai_api_key
    }
    __file_path: Path = _config.gpt3_data_path / "setting.json"

    @property
    def file_path(self) -> Path:
        return self.__class__.__file_path

    @root_validator(pre=True)
    def init(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if cls.__file_path.is_file():
            return json.loads(cls.__file_path.read_text("utf-8"))
        return values

    def save(self) -> None:
        self.file_path.write_text(self.json(), encoding="utf-8")


# 文件保存的setting，用于记载用户会话、系统配置
setting = Setting()
# 使用全局字典存储所有用户的会话信息
user_session: Dict[str, Session] = {}
# 指令block锁
user_lock: Dict[str, bool] = {}