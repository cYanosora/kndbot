from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from services import logger
from ._models import WithdrawBase
from nonebot import Driver, get_driver

withdraw_group_dict = {}
driver: Driver = get_driver()


@driver.on_bot_connect
async def _(bot: Bot):
    global withdraw_group_dict
    id = bot.self_id
    withdraw_group_dict[id] = []
    gl = [g["group_id"] for g in await bot.get_group_list()]
    for g in gl:
        if g not in withdraw_group_dict[id] and await WithdrawBase.exist_any_entry(g):
            withdraw_group_dict[id].append(g)
            logger.info(f"Bot({id})载入了群组{g}的撤回配置")


async def check(event: GroupMessageEvent) -> bool:
    # 检测群内是否有设置词条，没有就不匹配了
    global withdraw_group_dict
    if event.group_id not in withdraw_group_dict.get(str(event.self_id), []):
        return False

    # 将用户发言转化为可匹配的格式化问句
    entry = await WithdrawBase.message2entry(event.message)
    # 检测问句是否能匹配
    if entry and await WithdrawBase.check(event, entry):
        return True
    else:
        return False

