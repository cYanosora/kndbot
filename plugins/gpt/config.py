from pathlib import Path
from typing import Union, List
from pydantic import BaseSettings
from nonebot import get_driver
from services import logger
from nonebot.rule import to_me
from configs.path_config import DATA_PATH
import asyncio

class Config(BaseSettings):
    # 基础配置
    data_path: Union[Path, str] = DATA_PATH
    poe_token: str = ''
    gpt_token: str = ''
    proxy: str = 'http://127.0.0.1:7890'
    # 指令触发配置
    poe_command_prefix: List[str] = ['poe', 'Poe', 'POE']
    bing_command_prefix: List[str] = ['bing', 'Bing', 'BING']
    gpt_command_prefix: List[str] = ['chat', 'Chat', 'CHAT']
    need_at: bool = False
    # 会话配置
    poe_default_model: str = 'ChatGPT'
    poe_default_preset: str = ''
    bing_default_reply_mode: str = 'balanced'
    gpt_default_model: str = 'text-davinci-002-render-paid'
    gpt_default_preset: str = ''
    # 图片渲染
    image_render: bool = True
    image_limit: int = 200

    class Config:
        extra = "ignore"


# 初始化
config = Config.parse_obj(get_driver().config)
if config.poe_token:
    logger.info(f"加载poe token: {config.poe_token}")
else:
    logger.warning('没有配置poe token')
if config.gpt_token:
    logger.info(f"加载gpt token: {config.gpt_token}")
else:
    logger.warning('没有配置gpt token')
logger.info(f"加载代理: {config.proxy if config.proxy else '无'}")
logger.info(f"加载poe默认模型: {config.poe_default_model if config.poe_default_model else '无'}")
logger.info(f"加载poe默认人格: {config.poe_default_preset if config.poe_default_preset else '无'}")
logger.info(f"加载gpt默认模型: {config.gpt_default_model if config.gpt_default_model else '无'}")
logger.info(f"加载gpt默认人格: {config.gpt_default_preset if config.gpt_default_preset else '无'}")
if isinstance(config.poe_command_prefix, list):
    poe_matcher_params = {'cmd': config.poe_command_prefix[0], 'aliases': set(config.poe_command_prefix[1:])}
else:
    poe_matcher_params = {'cmd': config.poe_command_prefix}
if isinstance(config.bing_command_prefix, list):
    bing_matcher_params = {'cmd': config.bing_command_prefix[0], 'aliases': set(config.bing_command_prefix[1:])}
else:
    bing_matcher_params = {'cmd': config.bing_command_prefix}
if isinstance(config.gpt_command_prefix, list):
    gpt_matcher_params = {'cmd': config.gpt_command_prefix[0], 'aliases': set(config.gpt_command_prefix[1:])}
else:
    gpt_matcher_params = {'cmd': config.gpt_command_prefix}
if config.need_at:
    poe_matcher_params['rule'] = to_me()
    bing_matcher_params['rule'] = to_me()
    gpt_matcher_params['rule'] = to_me()
need_at = {}
if config.need_at:
    need_at['rule'] = to_me()
gpt_lock = asyncio.Lock()
bing_lock = asyncio.Lock()
poe_lock = asyncio.Lock()
