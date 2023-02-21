from pathlib import Path
from typing import List, Literal, Optional, Union
from nonebot import get_driver
from pydantic import BaseModel, Extra
from configs.path_config import DATA_PATH


class Config(BaseModel, extra=Extra.ignore):
    chatgpt_session_token: str = ""
    chatgpt_account: str = ""
    chatgpt_password: str = ""
    chatgpt_cd_time: int = 60
    chatgpt_proxies: Optional[str] = None
    chatgpt_refresh_interval: int = 30
    chatgpt_command: Union[str, List[str]] = "chat"
    chatgpt_to_me: bool = False
    chatgpt_timeout: int = 60
    chatgpt_api: str = "https://chat.openai.com"
    chatgpt_image: bool = False
    chatgpt_max_textlength: int = 250
    chatgpt_image_width: int = 500
    chatgpt_priority: int = 10
    chatgpt_block: bool = True
    chatgpt_private: bool = False
    chatgpt_scope: Literal["private", "public"] = "private"
    chatgpt_data: Path = DATA_PATH
    chatgpt_max_rollback: int = 5
    chatgpt_detailed_error: bool = False


# 读取env配置，否则取当前文件的默认配置
config = Config.parse_obj(get_driver().config)
