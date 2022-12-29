import re
import random
from nonebot import on_message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from manager import Config
from utils.utils import get_message_text
from .data_source import _fudu_list

__plugin_name__ = "复读 [Hidden]"
__plugin_task__ = {"fudu": "复读"}
__plugin_configs__ = {
    "FUDU_PROBABILITY": {"value": 0.7, "help": "复读概率", "default_value": 0.7}
}
Config.add_plugin_config(
    "_task",
    "DEFAULT_FUDU",
    True,
    help_="被动 复读 进群默认开关状态",
    default_value=True,
)


fudu = on_message(permission=GROUP, priority=100)


@fudu.handle()
async def _(event: GroupMessageEvent):
    if event.is_tome():
        return
    if get_message_text(event.json()):
        if get_message_text(event.json()).find("@yoisaki_kanade") != -1:
            await fudu.finish("复制粘贴的虚空艾特？", at_sender=True)
    add_msg, raw_message = messagePreprocess(str(event.message))
    if _fudu_list.size(event.group_id) == 0:
        _fudu_list.append(event.group_id, add_msg)
    elif _fudu_list.check(event.group_id, add_msg):
        _fudu_list.append(event.group_id, add_msg)
    else:
        _fudu_list.clear(event.group_id)
        _fudu_list.append(event.group_id, add_msg)
    if _fudu_list.size(event.group_id) > 2:
        if not _fudu_list.is_repeater(event.group_id):
            _fudu_list.set_repeater(event.group_id)
            if random.random() < 0.1:
                await fudu.finish("[[_task|fudu]]打断施法！")
            rst = raw_message
            if rst:
                if rst.endswith("打断施法！"):
                    rst = "打断" + rst
                await fudu.send(Message("[[_task|fudu]]" + rst))


def messagePreprocess(message: str):
    raw_message = message
    contained_images = {}
    images = re.findall(r'\[CQ:image.*?]', message)
    for i in images:
        contained_images.update({i: re.findall(r'\[.*file=(.*?),.*]', i)[0]})
    for i in contained_images:
        message = message.replace(i, f'[{contained_images[i]}]')
    return message, raw_message
