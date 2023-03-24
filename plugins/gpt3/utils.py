from typing import Union, Optional
from nonebot.adapters.onebot.v11 import MessageEvent, Bot, MessageSegment
from models.level_user import LevelUser
from .config import config
from .store import user_session, Session, setting


def get_session_owner(event: MessageEvent, target_id: Optional[str] = None) -> str:
    """ 获取当前事件的session_owner """
    if config.gpt3_chat_mode == 'public':
        session_owner = 'public'
    elif config.gpt3_chat_mode == 'group' and hasattr(event, 'group_id'):
        session_owner = f'g{target_id or event.group_id}'
    else:
        session_owner = f'u{target_id or event.user_id}'
    return session_owner


def get_user_session(session_owner: str) -> Session:
    """ 获取对应目标的session信息 """
    if session_owner not in user_session:
        user_session[session_owner] = Session(session_owner)
    if session_owner in setting.preset.keys():
        user_session[session_owner].preset = setting.preset[session_owner]
    return user_session[session_owner]


async def handle_msg(resp: str) -> Union[str, MessageSegment]:
    """ 处理回复，决定是图片发送还是文字发送 """
    # 如果开启图片渲染，且字数大于limit则会发送图片
    if setting.config['send_image'] and len(resp) > config.gpt3_image_limit:
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

