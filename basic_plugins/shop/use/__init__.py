from nonebot import on_command
from models.goods_info import GoodsInfo
from models.user_shop_gold_log import UserShopGoldLog
from services.log import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.params import CommandArg
from utils.utils import is_number
from models.bag_user import BagUser
from nonebot.adapters.onebot.v11.permission import GROUP
from services.db_context import db
from .data_source import effect, register_use, func_manager, build_params, NotMeetUseConditionsException

__plugin_name__ = "使用道具"
__plugin_type__ = '商店'
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    普通的使用道具
    序号、名称、数量、参数之间可以不使用空格隔开
    指令：
        使用 [序号或道具名称] ?[数量] ?[参数]  : 数量默认为1
    举例：
        使用杯面                 ：使用一个杯面道具
        使用杯面2                ：使用两个杯面道具
        使用11                  ：使用背包里序号为1的道具一次
        使用生日礼物2兑换康乃馨     ：使用一个生日礼物2道具，可以兑换被动道具康乃馨
    * 序号以 ”我的道具“ 为准 *
""".strip()
__plugin_settings__ = {
    "cmd": ["商店", "使用道具"],
}


use_props = on_command(
    "使用道具", aliases={"消耗道具", "使用", "消耗"}, priority=5, block=True, permission=GROUP
)


async def get_whatuse(msg: str, event: GroupMessageEvent):
    property_ = await BagUser.get_property(event.user_id, event.group_id, True)
    all_property_ = await BagUser.get_property(event.user_id, event.group_id)
    active_property_names = [i for i in all_property_.keys() if i in property_.keys()]
    passive_property_names = [i for i in all_property_.keys() if i not in property_.keys()]
    goods_list = await GoodsInfo.get_all_goods()
    goods_names = [i.goods_name for i in goods_list]
    active_property_names.sort(key=goods_names.index)
    for item in passive_property_names:
        if msg.startswith(item):
            raise ValueError("被动道具无法主动使用噢")
    if active_property_names:
        if sum([1 for u in [is_number(i) for i in msg.split()] if u]) == len(msg.split()):
            item_ids = [str(i) for i in range(1, len(active_property_names) + 1)]
            item_ids.reverse()
            for item_id in item_ids:
                if msg.startswith(item_id):
                    use_item = active_property_names[int(item_id) - 1]
                    left_info = msg[len(item_id):].strip()
                    break
            else:
                raise IndexError('诶...？你没有这个道具哦？')
        else:
            for item_name in active_property_names:
                if msg.startswith(item_name):
                    use_item = item_name
                    left_info = msg[len(use_item):].strip()
                    break
            else:
                raise IndexError('道具名称输错了哦')
        _tmp_text = "1" if not left_info else left_info
        _id = 0
        for i in _tmp_text:
            if i.isdigit():
                _id += 1
            else:
                break
        use_num = int(_tmp_text[:_id] or "1")
        other_info = _tmp_text[_id:].strip()
        _user_prop_count = property_[use_item]
        if use_num > _user_prop_count:
            raise ValueError(f"道具数量不足{use_num}个...要不再去买点？")
        if use_num > (n := func_manager.get_max_num_limit(use_item)):
            raise ValueError(f"该道具每次生效前只能使用 {n} 个哦")
        return use_item, use_num, other_info
    else:
        raise IndexError("您的背包里没有任何的道具噢")


@use_props.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await use_props.finish("你的用法不对哦，请好好阅读功能帮助！", at_sender=True)
    name = num = None
    text = ""
    try:
        name, num, text = await get_whatuse(msg, event)
    except IndexError as e:
        await use_props.finish(str(e), at_sender=True)
    except ValueError as e:
        await use_props.finish(str(e), at_sender=True)
    if not name or not num:
        return
    try:
        model, kwargs = build_params(bot, event, name, num, text)
        await func_manager.run_handle(type_="before_handle", param=model, **kwargs)
    except NotMeetUseConditionsException as e:
        if e.get_info() == "道具暂时无法生效，请等待后续更新":
            logger.warning(f"道具 {name} 暂时没有使用函数")
        await use_props.finish(e.get_info(), at_sender=True)
        return
    async with db.transaction():
        if await BagUser.delete_property(event.user_id, event.group_id, name, num):
            try:
                msg = await effect(bot, event, name, num, text, event.message)
            except NotMeetUseConditionsException as e:
                await BagUser.add_property(event.user_id, event.group_id, name, num)
                logger.warning(f"道具 {name} 暂时没有使用函数")
                await use_props.finish(e.get_info(), at_sender=True)
                return
            if msg:
                await use_props.send(msg, at_sender=True)
            elif func_manager.check_send_success_message(name):
                await use_props.send(f"使用道具 {name} {num} 次成功！", at_sender=True)
            logger.info(
                f"USER {event.user_id} GROUP {event.group_id} 使用道具 {name} {num} 次成功"
            )
            await UserShopGoldLog.add_shop_log(event.user_id, event.group_id, 1, name, num)
        else:
            await use_props.send(f"使用道具 {name} {num} 次失败！", at_sender=True)
            logger.warning(f"USER {event.user_id} GROUP {event.group_id} 使用道具 {name} {num} 次失败")
    await func_manager.run_handle(type_="after_handle", param=model, **kwargs)
