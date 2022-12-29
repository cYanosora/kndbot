from nonebot.internal.matcher import Matcher
from services import logger
from ._rule import check
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot

__plugin_name__ = "自助撤回词条检测 [Hidden]"
message_handle = on_message(priority=1, block=False, rule=check)


@message_handle.handle()
async def _(matcher: Matcher, bot: Bot, event: GroupMessageEvent):
    try:
        self_info = await bot.get_group_member_info(group_id=event.group_id, user_id=int(bot.self_id))
        # 检测bot自身是否是群管理员，不是则无需尝试撤回群员消息
        flag = True if self_info["role"] in ["owner", "admin"] else False
        # 检测对方是否是成员，不是则无需尝试撤回
        user_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
        flag = flag and True if user_info["role"] == "member" else False
    except:
        flag = False
    if flag:
        message_id = event.message_id
        try:
            await bot.delete_msg(message_id=message_id)
            logger.info(
                f"USER {event.user_id}, GROUP {event.group_id} "
                f"(自动撤回了消息，原文：{event.message})"
            )
            matcher.stop_propagation()
        except Exception as e:
            logger.warning(
                f"USER {event.user_id}, GROUP {event.group_id} "
                f"(自动撤回消息失败，原因：{e})"
            )
        return
