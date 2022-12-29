from nonebot import on_command
from services.log import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.params import CommandArg
from utils.utils import is_number
from models.bag_user import BagUser
from nonebot.adapters.onebot.v11.permission import GROUP
from services.db_context import db
from .data_source import effect, register_use, func_manager


__plugin_name__ = "使用道具"
__plugin_type__ = '商店'
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    普通的使用道具
    序号、名称、数量之间可以不使用空格隔开
    指令：
        使用 [序号或道具名称] ?[数量]   : 数量默认为1
    * 序号以 ”我的道具“ 为准 *
""".strip()
__plugin_settings__ = {
    "cmd": ["商店", "使用道具"],
}


use_props = on_command(
    "使用道具", aliases={"消耗道具", "使用", "消耗"}, priority=5, block=True, permission=GROUP
)


async def get_whatuse(msg: str, event: GroupMessageEvent):
    property_ = await BagUser.get_property(event.user_id, event.group_id)
    if property_:
        if sum([1 for u in [is_number(i) for i in msg.split()] if u]) == len(msg.split()):
            item_ids = [str(i) for i in range(1, len(property_) + 1)]
            item_ids.reverse()
            for item_id in item_ids:
                if msg.startswith(item_id):
                    use_item = list(property_.keys())[int(item_id) - 1]
                    use_num = msg[len(item_id):].strip()
                    break
            else:
                raise IndexError('诶...？你没有这个道具哦？')
        else:
            for item_name in property_.keys():
                if msg.startswith(item_name):
                    use_item = item_name
                    use_num = msg[len(use_item):].strip()
                    break
            else:
                raise IndexError('道具名称输错了哦')
        use_num = 1 if not use_num else use_num
        if not is_number(use_num) or int(use_num) <= 0:
            raise ValueError('道具数量要是数字且大于0！')
        else:
            use_num = int(use_num)
            _user_prop_count = property_[use_item]
            if use_num > _user_prop_count:
                raise ValueError(f"道具数量不足{use_num}个...要不再去买点？")
            if use_num > (n := func_manager.get_max_num_limit(use_item)):
                raise ValueError(f"该道具每次生效前只能使用 {n} 个哦")
            return use_item, use_num
    else:
        raise IndexError("您的背包里没有任何的道具噢")


@use_props.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await use_props.finish("你的用法不对哦，请好好阅读功能帮助！", at_sender=True)
    name = num = None
    try:
        name, num = await get_whatuse(msg, event)
    except IndexError as e:
        await use_props.finish(str(e), at_sender=True)
    except ValueError as e:
        await use_props.finish(str(e), at_sender=True)
    if not name or not num:
        return
    async with db.transaction():
        if await BagUser.delete_property(
            event.user_id, event.group_id, name, num
        ):
            msg = await effect(bot, event, name, num)
            if msg:
                await use_props.send(msg, at_sender=True)
            elif func_manager.check_send_success_message(name):
                await use_props.send(f"你使用了道具 {name} × {num} 个", at_sender=True)
            logger.info(
                f"USER {event.user_id} GROUP {event.group_id} 使用道具 {name} {num} 次成功"
            )
        else:
            await use_props.send(f"使用道具 {name} × {num} 次失败了...怎么回事呢？", at_sender=True)
            logger.info(
                f"USER {event.user_id} GROUP {event.group_id} 使用道具 {name} {num} 次失败"
            )
