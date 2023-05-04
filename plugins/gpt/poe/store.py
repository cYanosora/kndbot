import traceback
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field, root_validator
from .poeapi import client
from ..config import config as _config
try:
    import ujson as json
except ModuleNotFoundError:
    import json


class Session(BaseModel):
    preset: Dict[str, str] = Field(default_factory=dict)
    model: Dict[str, str] = Field(default_factory=dict)
    __file_path: Path = _config.data_path / "poe_setting.json"

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
        """ poe api会话 """
        model = self.get_model(id)
        preset = self.get_preset(id)
        try:
            return await client.request_api(msg, model, preset)
        except:
            traceback.print_exc()
            return '出错了，请稍后再试\n频繁出现此提示请联系master'

    def set_preset(self, id: str, preset: str):
        self.preset[id] = preset
        self.save()

    def set_model(self, id: str, model: str):
        self.model[id] = model
        self.save()

    def get_preset(self, id: str):
        return self.preset.get(id, None) or _config.poe_default_preset

    def get_model(self, id: str):
        return self.model.get(id, None) or _config.poe_default_model


# 记载用户会话配置
session_data = Session()