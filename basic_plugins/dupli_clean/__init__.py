from typing import Any, Dict
from nonebot.adapters.onebot.v11 import Event, Bot, PokeNotifyEvent, PrivateMessageEvent
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from configs.config import MAIN_BOT, SUB_BOT, AUX_BOT, EXT_BOT, FIF_BOT
from utils.utils import get_message_at

recent_event: Dict[str, Any] = {}


# 多个bot号在同一个群时防止重复触发指令的措施
@event_preprocessor
async def _(bot: Bot, event: Event):
    global recent_event
    selfid = bot.self_id
    bot_ids = [MAIN_BOT, SUB_BOT, AUX_BOT, EXT_BOT, FIF_BOT]
    # 戳一戳事件回避
    if isinstance(event, PokeNotifyEvent) and event.target_id in bot_ids:
        return
    if isinstance(event, PrivateMessageEvent):
        return
    bot_ids.remove(int(selfid))
    try:
        user_id = int(event.get_user_id())
    except:
        user_id = 0
    if user_id in bot_ids:
        raise IgnoredException('忽略bot互相触发的指令')
    # 使用了at指定bot，无需担心bot重复触发事件
    if hasattr(event, "raw_message"):
        ats = get_message_at(event.raw_message)
        if int(selfid) in ats:
            return
    try:
        combine = f"{event.get_type()}_{event.get_session_id()}"
    except ValueError:
        return
    if not recent_event.get(selfid):
        recent_event[selfid] = []
    for each_bot in recent_event.keys():
        if each_bot == selfid:
            continue
        if any(map(lambda each_event: each_event == combine, recent_event[each_bot])):
            recent_event[selfid].clear()
            raise IgnoredException("忽略bot触发的相同事件")
    recent_event[selfid].clear()
    recent_event[selfid].append(combine)
