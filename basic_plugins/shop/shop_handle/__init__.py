from nonebot.rule import to_me
from utils.imageutils import text2image, pic2b64
from .data_source import create_shop_help, delete_goods, update_goods, register_goods, parse_goods_info, GoodsInfo
from nonebot.adapters.onebot.v11 import MessageEvent, Message, GROUP
from nonebot import on_command
from utils.message_builder import image
from nonebot.permission import SUPERUSER
from utils.utils import is_number, scheduler
from nonebot.params import CommandArg
from services.log import logger


__plugin_name__ = "查看商店"
__plugin_type__ = '商店'
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    商店项目
    指令：
        查看商店/查看商品/道具商店
""".strip()
__plugin_superuser_usage__ = """
usage：
    商品操作
    指令：
        添加商品 name:[名称] *[键:值]
        删除商品 [名称或序号]
        修改商品 name:[名称] *[键:值]
    注意：
        [键:值]支持以下类型
        name:[名称] price:[价格] des:[简介] effect:[效果]
        ?discount:[折扣](小数) ?limit_time:[限时时间](小时) ?daily_limit:[每日限制购买次数]
        ?is_passive:[是否为被动道具] ?is_show:[是否在商店内展示] ?icon:[道具图标文件名]
    示例：
        添加商品 name:奏宝的八音盒 price:2525 des:奏妈留下来的珍贵回忆.. effect:好感翻倍
        添加商品 name:奏宝的运动衫 price:2525 des:奏宝时常穿在身的最强装备 discount:0.4 limit_time:90
        添加商品 name:奏宝的乐谱   price:2525 des:奏宝为拯救他人而创作的曲子 discount:0.5 limit_time:90
        删除商品 2
        修改商品 name:1 price:900   修改序号为1的商品的价格为900
        修改商品 name:2 price:-1    修改序号为2的商品的价格为-1(无法售出)
    * 修改商品只需添加需要值即可 *
""".strip()
__plugin_settings__ = {
    "cmd": ["查看商店", "商店"],
}
__plugin_block_limit__ = {
    "limit_type": "group"
}


shop_help = on_command("查看商店", aliases={"查看商品", "道具商店"}, permission=GROUP, priority=5, block=True)
shop_help_bak = on_command("商店", permission=GROUP, priority=5, rule=to_me(), block=True)
shop_add_goods = on_command("添加商品", priority=5, permission=SUPERUSER, block=True)
shop_del_goods = on_command("删除商品", priority=5, permission=SUPERUSER, block=True)
shop_update_goods = on_command("修改商品", priority=5, permission=SUPERUSER, block=True)


@shop_help.handle()
async def _():
    await shop_help.send(image(b64=await create_shop_help()))


@shop_help_bak.handle()
async def _():
    await shop_help.send(image(b64=await create_shop_help()))


@shop_add_goods.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        data = parse_goods_info(msg)
        if isinstance(data, str):
            await shop_add_goods.finish(data)
        if not data.get("name") or not data.get("price") or not data.get("des") or not data.get("effect"):
            await shop_add_goods.finish("name:price:des:effect 参数不可缺少！")
        if await register_goods(**data):
            await shop_add_goods.send(
                image(b64=pic2b64(text2image(
                    f"添加商品 {data['name']} 成功！\n"
                    f"名称：{data['name']}\n"
                    f"价格：{data['price']}金币\n"
                    f"简介：{data['des']}\n"
                    f"效果：{data['effect']}\n"
                    f"折扣：{data.get('discount')}\n"
                    f"限时：{data.get('limit_time')}\n"
                    f"限制购买：{data.get('daily_limit')}\n"
                    f"被动道具：{data.get('is_passive')}\n"
                    f"商店展示：{data.get('is_show')}\n"
                    f"图标：{data.get('icon')}",
                ))),
                at_sender=True
            )
            logger.info(f"USER {event.user_id} 添加商品 {msg} 成功")
        else:
            await shop_add_goods.send(f"添加商品 {msg} 失败了...", at_sender=True)
            logger.warning(f"USER {event.user_id} 添加商品 {msg} 失败")


@shop_del_goods.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        name = ""
        id_ = 0
        if is_number(msg):
            id_ = int(msg)
        else:
            name = msg
        rst, goods_name, code = await delete_goods(name, id_)
        if code == 200:
            await shop_del_goods.send(f"删除商品 {goods_name} 成功了...", at_sender=True)
            logger.info(f"USER {event.user_id} 删除商品 {goods_name} 成功")
        else:
            await shop_del_goods.send(f"删除商品 {goods_name} 失败了...", at_sender=True)
            logger.info(f"USER {event.user_id} 删除商品 {goods_name} 失败")


@shop_update_goods.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        data = parse_goods_info(msg)
        if isinstance(data, str):
            await shop_add_goods.finish(data)
        if not data.get("name"):
            await shop_add_goods.finish("name 参数不可缺少！")
        flag, name, text = await update_goods(**data)
        if flag:
            await shop_update_goods.send(f"修改商品 {name} 成功了...\n{text}", at_sender=True)
            logger.info(f"USER {event.user_id} 修改商品 {name} 数据 {text} 成功")
        else:
            await shop_update_goods.send(name, at_sender=True)
            logger.info(f"USER {event.user_id} 修改商品 {name} 数据 {text} 失败")

