from typing import Any, Dict
from nonebot.adapters.onebot.v11 import Event, Bot
from nonebot.exception import IgnoredException
from nonebot.internal.matcher import Matcher
from nonebot.message import run_preprocessor
from utils.utils import get_message_at

recent_event: Dict[str, Any] = {}


# 多个bot号在同一个群时防止重复触发指令的措施
@run_preprocessor
async def _(matcher: Matcher, bot: Bot, event: Event):
    global recent_event
    selfid = bot.self_id

    if hasattr(event, "raw_message"):
        ats = get_message_at(event.raw_message)
        if int(selfid) in ats and matcher.plugin_name != 'petpet':
            return
    combine = f'{event.get_session_id()}:{matcher.plugin_name}'
    if not recent_event.get(selfid):
        recent_event[selfid] = []
    for each_bot in recent_event.keys():
        if each_bot == selfid:
            continue
        for each_event in recent_event[each_bot]:
            if combine == each_event:
                matcher.stop_propagation()
                raise IgnoredException("相同事件")
    recent_event[selfid].clear()
    recent_event[selfid].append(combine)
