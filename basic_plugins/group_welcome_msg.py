from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from configs.path_config import DATA_PATH
from utils.message_builder import image

try:
    import ujson as json
except ModuleNotFoundError:
    import json

__plugin_name__ = "查看群欢迎消息"
__plugin_type__ = "其他"
__plugin_usage__ = """
usage：
    查看当前的群欢迎消息
    群管自定义群欢迎消息请使用 自定义群欢迎消息 功能
    指令：
        查看群欢迎消息
""".strip()
__plugin_settings__ = {
    "cmd": ["查看群欢迎消息"],
}

view_custom_welcome = on_command("查看群欢迎消息", permission=GROUP, priority=5, block=True)


@view_custom_welcome.handle()
async def _(event: GroupMessageEvent):
    img = ""
    msg = ""
    if (DATA_PATH / "custom_welcome_msg" / f"{event.group_id}.jpg").exists():
        img = image(DATA_PATH / "custom_welcome_msg" / f"{event.group_id}.jpg")
    custom_welcome_msg_json = (
       DATA_PATH / "custom_welcome_msg" / "custom_welcome_msg.json"
    )
    if custom_welcome_msg_json.exists():
        data = json.load(open(custom_welcome_msg_json, "r"))
        if data.get(str(event.group_id)):
            msg = data[str(event.group_id)]
            if msg.find("[at]") != -1:
                msg = msg.replace("[at]", "")
    if img or msg:
        await view_custom_welcome.finish(msg + img, at_sender=True)
    else:
        await view_custom_welcome.finish("当前还没有自定义群欢迎消息哦", at_sender=True)
