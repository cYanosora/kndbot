from nonebot import on_command
from services.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.params import CommandArg
from utils.message_builder import image
from utils.utils import is_number
from models.bag_user import BagUser
from services.db_context import db
from nonebot.adapters.onebot.v11.permission import GROUP
from models.goods_info import GoodsInfo
import time


__plugin_name__ = "购买道具"
__plugin_type__ = "商店"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    从商店中购买道具，可以购买的道具信息请发送 '查看商店' 获取
    序号、名称、数量之间可以不使用空格隔开
    指令:
        购买 [序号或名称] ?[数量]        : 数量默认为1
    示例:
        购买 好感度双倍加持卡Ⅰ
        购买 1 4
""".strip()
__plugin_settings__ = {
    "cmd": ["商店", "购买道具", "购买商品"],
}

buy = on_command("购买", aliases={"购买道具", "购买商品"}, priority=5, block=True, permission=GROUP)


async def get_whatbuy(msg: str):
    goods_list = [
        x
        for x in await GoodsInfo.get_all_goods()
        if x.goods_limit_time > time.time() or x.goods_limit_time == 0
    ]
    # 传入的文本完全是数字
    if sum([1 for u in [is_number(i) for i in msg.split()] if u]) == len(msg.split()):
        good_ids = [str(i) for i in range(1, len(goods_list) + 1)]
        good_ids.reverse()
        for good_id in good_ids:
            if msg.startswith(good_id):
                buy_good = goods_list[int(good_id) - 1]
                buy_num = msg[len(good_id):].strip()
                break
        else:
            raise IndexError('请输入正确的商品id！')
    # 传入的文本含非数字，分为商品名称与购买数量
    else:
        goods_name_list = [x.goods_name for x in goods_list]
        for good_name in goods_name_list:
            if msg.startswith(good_name):
                print(goods_name_list.index(good_name))
                buy_good = goods_list[goods_name_list.index(good_name)]
                buy_num = msg[len(good_name):].strip()
                break
        else:
            raise IndexError('请输入正确的商品名称！')
    buy_num = 1 if not buy_num else buy_num
    if not is_number(buy_num) or int(buy_num) <= 0:
        raise ValueError('购买的数量要是数字且大于0！')
    else:
        print(buy_good, buy_num)
        return buy_good, int(buy_num)


@buy.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    if arg.extract_plain_text().strip() in ["奏宝", "小奏", "宵崎奏", "奏", "kanade", "knd"]:
        await buy.finish("你光想想就好了，我才不可能卖给你的啦~" + image("tehe.png", "kanade/shop"), at_sender=True)
    msg = arg.extract_plain_text().strip()
    if not msg:
        await buy.finish("你的用法不对哦：购买 [道具序号或名称]", at_sender=True)
    buy_good = buy_num = None
    try:
        buy_good, buy_num = await get_whatbuy(msg)
    except ValueError as e:
        await buy.finish(str(e), at_sender=True)
    except IndexError as e:
        await buy.finish(str(e), at_sender=True)
    if not buy_good or not buy_num:
        return
    async with db.transaction():
        if (
            await BagUser.get_gold(event.user_id, event.group_id)
        ) < buy_good.goods_price * buy_num * buy_good.goods_discount:
            await buy.finish("啊咧..？您的金币好像不太够哦", at_sender=True)
        if await BagUser.buy_property(event.user_id, event.group_id, buy_good, buy_num):
            await buy.send(
                f"花费 {buy_good.goods_price * buy_num * buy_good.goods_discount} "
                f"金币购买 {buy_good.goods_name} × {buy_num} 成功！",
                at_sender=True,
            )
            logger.info(
                f"USER {event.user_id} GROUP {event.group_id} "
                f"花费 {buy_good.goods_price*buy_num} "
                f"金币购买 {buy_good.goods_name} × {buy_num} 成功！"
            )
        else:
            await buy.send(f"{buy_good.goods_name} 购买失败！", at_sender=True)
            logger.info(
                f"USER {event.user_id} GROUP {event.group_id} "
                f"花费 {buy_good.goods_price * buy_num * buy_good.goods_discount} "
                f"金币购买 {buy_good.goods_name} × {buy_num} 失败！"
            )
