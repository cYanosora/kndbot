from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field, root_validator
from .openai import client
from ..config import config as _config
try:
    import ujson as json
except ModuleNotFoundError:
    import json


class Session(BaseModel):
    preset: Dict[str, str] = Field(default_factory=dict)
    model: Dict[str, str] = Field(default_factory=dict)
    session: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    __file_path: Path = _config.data_path / "gpt_setting.json"

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
        """ gpt api会话 """
        model = self.get_model(id)
        preset = self.get_preset(id)
        conversation_id = parent_id = ""
        session = self.get_session(id)
        if session is not None:
            conversation_id, parent_id = session['conversation_id'], session['parent_id']
        try:
            data = await client.request_api(msg, model, preset, conversation_id, parent_id)
            if isinstance(data, str):
                return data
            self.set_session(id, **data)
            return data['message']
        except:
            return '出错了，请稍后再试\n频繁出现此提示请联系master'

    def set_preset(self, id: str, preset: str):
        self.preset[id] = preset
        self.save()

    def set_model(self, id: str, model: str):
        self.model[id] = model
        self.save()

    def get_preset(self, id: str):
        return self.preset.get(id, None) or _config.gpt_default_preset

    def get_model(self, id: str):
        return self.model.get(id, None) or _config.gpt_default_model

    def get_session(self, id: str):
        return self.session.get(id)

    def set_session(self, id: str, **data):
        self.session[id] = {
            'conversation_id': data["conversation_id"],
            'parent_id': data["parent_id"]
        }
        self.save()

    def del_session(self, id: str):
        del self.session[id]
        self.save()


# 记载用户会话配置
session_data = Session()