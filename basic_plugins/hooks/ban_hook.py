from nonebot.message import run_preprocessor, IgnoredException
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    MessageEvent,
    PokeNotifyEvent,
)
from models.ban_info import BanInfo


# 检查是否bot被ban(禁言) or 用户是否被ban
@run_preprocessor
async def _(bot: Bot, event: Event):
    if isinstance(event, MessageEvent) or isinstance(event, PokeNotifyEvent):
        user_id = event.user_id
        group_id = event.group_id if hasattr(event, "group_id") else None
        # 超管不受限制
        if str(user_id) in bot.config.superusers:
            return
        # 检测bot是否被禁言
        if group_id and await BanInfo.is_ban(None, group_id):
            raise IgnoredException("bot处于禁言中")
        # 检测用户群内是否被封禁
        if group_id and await BanInfo.is_ban(user_id, group_id):
            raise IgnoredException("用户处于黑名单中")  # 针对一些功能中的特殊拉黑行为

