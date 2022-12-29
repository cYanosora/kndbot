from nonebot import on_command
from utils.utils import get_message_img
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.params import CommandArg
from ._data_source import custom_group_welcome, del_group_welcome
from nonebot.adapters.onebot.v11.permission import GROUP
from manager import Config
from services.log import logger


__plugin_name__ = "设置群欢迎消息 [Admin]"
__plugin_type__ = "群相关"
__plugin_version__ = 0.1
__plugin_usage__ = """
admin_usage：
    指令:
        设置群欢迎消息 ?[文本] ?[图片]
        删除群欢迎消息      :使群欢迎消息恢复默认
    示例:
        设置群欢迎消息 欢迎你[at]
    注意:    
        可以通过[at]来确认是否艾特新成员
        目前设置后将不能恢复至默认欢迎消息
""".strip()
__plugin_settings__ = {
    "admin_level": Config.get_config("admin_bot_manage", "SET_GROUP_WELCOME_MESSAGE_LEVEL"),
    "cmd": ["设置群欢迎消息", "设置进群欢迎消息"]
}

custom_welcome = on_command(
    "设置群欢迎消息",
    aliases={"设置进群欢迎消息"},
    permission=GROUP,
    priority=3,
    block=True,
)

default_welcome = on_command(
    "删除群欢迎消息",
    aliases={"删除进群欢迎消息"},
    permission=GROUP,
    priority=3,
    block=True,
)


@custom_welcome.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    try:
        msg = arg.extract_plain_text().strip()
        img = get_message_img(event.json())
        if not msg and not img:
            await custom_welcome.finish("请了解使用说明后再自行设置", at_sender=True)
        logger.info(f"USER {event.user_id} GROUP {event.group_id} 自定义群欢迎消息：{msg}")
    except Exception as e:
        logger.error(f"自定义进群欢迎消息发生错误 {type(e)}：{e}")
        await custom_welcome.finish("发生了一些未知错误...")
    else:
        await custom_welcome.finish(
            await custom_group_welcome(msg, img, event.user_id, event.group_id),
            at_sender=True
        )


@default_welcome.handle()
async def _(event: GroupMessageEvent):
    await default_welcome.finish(
        await del_group_welcome(event.user_id, event.group_id),
        at_sender=True
    )