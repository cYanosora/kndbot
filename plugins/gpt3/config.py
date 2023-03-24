from pathlib import Path
from typing import Literal, Union, List
from pydantic import BaseSettings
from nonebot import get_driver
from services import logger
from nonebot.rule import to_me
from configs.path_config import DATA_PATH


class Config(BaseSettings):
    openai_api_key: str = ''
    gpt3_data_path: Union[Path, str] = DATA_PATH
    gpt3_command_prefix: List[str] = ['chat', 'Chat', 'CHAT']
    gpt3_default_preset: str = ''
    gpt3_need_at: bool = False
    gpt3_image_render: bool = True
    gpt3_image_limit: int = 200
    gpt3_max_tokens: int = 1024
    gpt3_model: str = 'gpt-3.5-turbo'
    gpt3_chat_count_per_day: int = 200
    gpt3_proxy: str = 'http://127.0.0.1:7890'
    gpt3_chat_mode: Literal["public", "group", "user"] = 'group'

    class Config:
        extra = "ignore"


config = Config.parse_obj(get_driver().config)

if config.openai_api_key:
    logger.info(f"加载api keys: {config.openai_api_key}")
else:
    logger.warning('没有配置api key')
logger.info(f"加载代理: {config.gpt3_proxy if config.gpt3_proxy else '无'}")
logger.info(f"加载默认人格: {config.gpt3_default_preset}")


# 基本会话
if isinstance(config.gpt3_command_prefix, list):
    matcher_params = {'cmd': config.gpt3_command_prefix[0], 'aliases': set(config.gpt3_command_prefix[1:])}
else:
    matcher_params = {'cmd': config.gpt3_command_prefix}

if config.gpt3_need_at:
    matcher_params['rule'] = to_me()

# 其他命令
need_at = {}
if config.gpt3_need_at:
    need_at['rule'] = to_me()

# 聊天人格
ai_preset = '以下是与AI助手的对话。助理乐于助人、富有创意、聪明而且非常友好。'
knd_preset = '''填写话术的位置'''
