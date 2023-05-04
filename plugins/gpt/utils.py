from typing import Union, Optional
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, Bot
from models.level_user import LevelUser
from .config import config, poe_lock, bing_lock, gpt_lock
from .poe import poe_session_data
from .bing import bing_session_data
from .chatgpt import gpt_session_data


async def ask(type: str, user: str, msg: str) -> Optional[str]:
    resp = None
    if type == 'poe':
        async with poe_lock:
            resp = await poe_session_data.get_chat_response(user, msg)
    elif type == 'bing':
        async with bing_lock:
            resp = await bing_session_data.get_chat_response(user, msg)
    elif type == 'gpt':
        async with gpt_lock:
            resp = await gpt_session_data.get_chat_response(user, msg)
    return resp


def get_avail_reply_modes():
    return {'创造': 'creative', '均衡': 'balanced', '准确': 'precise'}


def get_avail_models():
    return [
        'Sage', 'Claude+', 'Claude-instant', 'GPT-4', 'cuteknd',
        'Dragonfly', 'NeevaAI', 'ChatGPT'
    ]


def get_session_owner(event: MessageEvent, target_id: Optional[str] = None) -> str:
    """ 获取当前事件的session_owner """
    return f'g{target_id or event.group_id}' if hasattr(event, 'group_id') else f'u{target_id or event.user_id}'


async def handle_msg(resp: str) -> Union[str, MessageSegment]:
    """ 处理回复，决定是图片发送还是文字发送 """
    # 如果开启图片渲染，且字数大于limit则会发送图片
    if config.image_render and len(resp) > config.image_limit:
        if resp.count("```") % 2 != 0:
            resp += "\n```"
        from nonebot_plugin_htmlrender import md_to_pic
        img = await md_to_pic(resp)
        return MessageSegment.image(img)
    else:
        return resp


def checker_super(event: MessageEvent, bot: Bot) -> bool:
    """ 检查用户是否为master """
    return str(event.user_id) in bot.config.superusers


async def checker_admin(event: MessageEvent, bot: Bot) -> bool:
    """ 检查用户是否为管理员 """
    return checker_super(event, bot) or await LevelUser.check_level(event.user_id, event.group_id if hasattr(event, 'group_id') else 0, 5)

