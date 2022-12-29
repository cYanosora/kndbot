from nonebot import on_regex
from services.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, GROUP
from nonebot.typing import T_State
from .data_source import get_epic_free

__plugin_name__ = "epic免费游戏"
__plugin_type__ = "资讯类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    可以不玩，不能没有，每日白嫖
    指令：
        epic/epic免费游戏       : 获取E宝今日游戏折扣信息
""".strip()
__plugin_settings__ = {
    "cmd": ["epic", "epic免费游戏"],
}

__plugin_cd_limit__ = {"cd": 30, "rst": "不久前才发了epic折扣资讯诶，看看上面的消息吧，不然还请[cd]秒后再用呢~[at]", "limit_type": "group",}
__plugin_block_limit__ = {"rst": "别急，还在获取折扣信息中..."}
__plugin_count_limit__ = {
    "max_count": 3,
    "limit_type": "user",
    "rst": "你今天已经查询过多次了哦，还请明天再继续呢[at]",
}

epic = on_regex("^epic(?:免费游戏)?$", priority=5, permission=GROUP, block=True)

@epic.handle()
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    Type_Event = "Private"
    if isinstance(event, GroupMessageEvent):
        Type_Event = "Group"
    await epic.send("正在获取E宝今日折扣信息中...")
    msg_list, code = await get_epic_free(bot, Type_Event)
    if code == 404:
        await epic.send(msg_list)
    elif isinstance(event, GroupMessageEvent):
        await bot.send_group_forward_msg(group_id=event.group_id, messages=msg_list)
    else:
        for msg in msg_list:
            await bot.send_private_msg(user_id=event.user_id, message=msg)
    logger.info(
        f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
        f" 获取epic免费游戏"
    )
