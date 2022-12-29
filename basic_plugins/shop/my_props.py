from nonebot.adapters.onebot.v11 import ActionFailed
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from nonebot import on_command
from services.log import logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from models.bag_user import BagUser
from nonebot.adapters.onebot.v11.permission import GROUP


__plugin_name__ = "我的道具"
__plugin_type__ = '商店'
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    查看自己的道具
    指令：
        我的道具/查看道具
""".strip()
__plugin_settings__ = {
    "cmd": ["商店", "我的道具", "查看道具"],
}


my_props = on_command("我的道具", aliases={"查看道具"}, priority=5, block=True, permission=GROUP)


@my_props.handle()
async def _(event: GroupMessageEvent):
    props = await BagUser.get_property(event.user_id, event.group_id)
    if props:
        rst = ""
        for i, p in enumerate(props.keys()):
            rst += f"{i+1}.{p}\t×{props[p]}\n"
        try:
            await my_props.send("\n" + rst[:-1], at_sender=True)
        except ActionFailed:
            await my_props.send(
                image(b64=pic2b64(text2image(rst, color="#f9f6f2"))),
                at_sender=True
            )
        logger.info(f"USER {event.user_id} GROUP {event.group_id} 查看我的道具")
    else:
        await my_props.finish("您尚未拥有任何道具噢~", at_sender=True)
