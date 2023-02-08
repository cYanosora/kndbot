import os
from pathlib import Path
from typing import Tuple, Any
from nonebot import on_regex, on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message, GROUP
from nonebot.internal.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.rule import to_me
from models.group_member_info import GroupInfoUser
from models.friend_user import FriendUser
from services.log import logger
from configs.config import NICKNAME
import random
from utils.utils import cn2py

try:
    import ujson as json
except ModuleNotFoundError:
    import json

__plugin_name__ = "roll"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    随机数字 或 随机选择事件
    指令：
        roll                    : 随机 0-100 的数字
        roll *[文本]             : 随机从选项中选取一个进行答复
        @bot [选项]还是[选项]      : 同上，较人性化的触发方式   
    示例：
        roll 吃饭 睡觉 打游戏
        小奏，肝榜还是开摆
""".strip()
__plugin_settings__ = {
    "cmd": ["roll"],
}

data = {}
ban_msg = []
replace_word = []
not_trigger_word = ["咱", "你", "我", "他", "她", "这", "那", "它", "那个", "这个"]
roll = on_regex(r"^roll(.*)", priority=4, permission=GROUP, block=True)
roll3 = on_keyword({"还是"}, rule=to_me(), permission=GROUP, priority=4, block=True)


@roll.handle()
async def _(event: MessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    msg = reg_group[0].strip().split()
    new_msg = []
    for each in msg:
        # 文本过长，也许不是触发了命令
        if len(each) >= 20:
            return
        # 文本过短，也许不是触发了命令
        if each in not_trigger_word:
            return
        # 替换选项中的称呼词
        for i in replace_word:
            each = each.replace(i['bef'], i['aft'])
        new_msg.append(each)

    # 选项只有一种
    if len(new_msg) != 0:
        if len(new_msg) == 1 or new_msg.count(new_msg[0]) == len(new_msg):
            await roll.finish("这不是只有一个选项嘛...o(><；)oo")

    await send_msg(roll.__call__(), new_msg, event)
    logger.info(
        f"(USER {event.user_id}, "
        f"GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) "
        f"发送roll：{msg}"
    )


@roll3.handle()
async def _(event: MessageEvent):
    global data
    global ban_msg
    global replace_word
    if not data:
        init_json()
    msg_str = event.get_plaintext().strip()
    for i in replace_word:
        msg_str = msg_str.replace(i['bef'], i['aft'])
    msg = msg_str.split("还是")
    # 文本不完全
    if "" in msg:
        return
    # 文本过长
    if len(max(msg)) >= 20:
        return
    # 文本过短
    for i in msg:
        if i in not_trigger_word:
            return
    # 文本只有一种选项
    if msg.count(msg[0]) == len(msg):
        await roll3.finish("这不是只有一个选项嘛...o(><；)oo")
    await send_msg(roll3.__call__(), msg, event)
    logger.info(
        f"(USER {event.user_id}, "
        f"GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) "
        f"发送roll：{msg}"
    )


async def send_msg(matcher: Matcher, msg: list, event: MessageEvent):
    global data
    global ban_msg
    global replace_word
    if not data:
        init_json()
    # 获取对象名称
    try:
        user_name = event.sender.card or event.sender.nickname
    except AttributeError:
        user_name = ""
    try:
        if isinstance(event, GroupMessageEvent):
            tmp_user_name = await GroupInfoUser.get_group_member_nickname(
                event.user_id, event.group_id
            )
            user_name = tmp_user_name if tmp_user_name else user_name
        else:
            tmp_user_name = await FriendUser.get_friend_nickname(event.user_id)
            user_name = tmp_user_name if tmp_user_name else user_name
    except AttributeError:
        pass
    if not msg:
        if user_name:
            await matcher.finish(f"{user_name}抽到的数字是 {random.randint(0, 100)} 哦")
        else:
            await matcher.finish(f"抽到的数字是 {random.randint(0, 100)} 哦", at_sender=True)

    for content in msg:
        for each_baninfo in ban_msg:
            if cn2py(content) == each_baninfo['ban_word']:
                await matcher.finish(f"{each_baninfo['ban_reply']}", at_sender=True)
                return
    if random.random() < 0.05:
        await matcher.finish(f"{NICKNAME}建议{user_name if user_name else '你'}都别做呢")
    else:
        await matcher.finish(Message(f"{NICKNAME}建议{user_name + '桑' if user_name else '你'}{random.choice(msg)}呢"))


def init_json():
    global data
    global ban_msg
    global replace_word
    data_file = Path(os.path.join(os.path.dirname(__file__), "data_source.json")).absolute()
    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "quotation" not in data.keys():
                ban_msg = []
            else:
                ban_msg = data.get("quotation")
            if "replace" not in data.keys():
                replace_word = []
            else:
                replace_word = data.get("replace")
    else:
        data = {}
