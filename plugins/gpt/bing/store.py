from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field, root_validator
from .bingapi import client
from ..config import config as _config
try:
    import ujson as json
except ModuleNotFoundError:
    import json

class Session(BaseModel):
    reply_mode: Dict[str, str] = Field(default_factory=dict)
    __file_path: Path = _config.data_path / "bing_setting.json"

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

    async def get_chat_response(self, id: str, msg: str) -> str:
        """ bing api会话 """
        reply_mode = self.get_reply_mode(id)
        try:
            return await client.request_api(msg, reply_mode)
        except:
            return '出错了，请稍后再试\n频繁出现此提示请联系master'

    def set_reply_mode(self, id: str, preset: str):
        self.reply_mode[id] = preset
        self.save()

    def get_reply_mode(self, id: str):
        return self.reply_mode.get(id, None) or _config.bing_default_reply_mode


# 记载用户会话配置
session_data = Session()