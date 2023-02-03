from nonebot import on_command
from utils.message_builder import image
from ._data_source import create_bag_image
from services.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from models.bag_user import BagUser
from nonebot.adapters.onebot.v11.permission import GROUP


__plugin_name__ = "我的道具"
__plugin_usage__ = """
usage：
    我的道具
    指令：
        我的道具
""".strip()
__plugin_type__ = '商店'
__plugin_version__ = 0.1
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["我的道具", "商店"],
}


my_props = on_command("我的道具", priority=5, block=True, permission=GROUP)


@my_props.handle()
async def _(event: GroupMessageEvent):
    props = await BagUser.get_property(event.user_id, event.group_id)
    if not props:
        await my_props.finish("您的背包里没有任何的道具噢~", at_sender=True)
    img = await create_bag_image(props)
    if not img:
        await my_props.finish("您的背包里没有任何的道具噢~", at_sender=True)
    await my_props.send(image(b64=img))
    logger.info(f"USER {event.user_id} GROUP {event.group_id} 查看我的道具")
