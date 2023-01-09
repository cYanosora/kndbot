import re
from nonebot import on_command, on_keyword
from nonebot.adapters.onebot.v11 import Message, GROUP, MessageEvent, PrivateMessageEvent, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg, EventPlainText, EventToMe
from plugins.what.data_source import get_content
from utils.limit_utils import ignore_mute
from manager import plugins2cd_manager


__plugin_name__ = "缩写查询/梗百科"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    可以查询缩写话或者梗的原意，小众词汇可能查不到
    指令：
        百科 [文本]
        [文本] 是什么/是啥/是谁
        缩写/缩写查询 [文本]
""".strip()
__plugin_settings__ = {
    "cmd": ["缩写", "梗百科", "缩写查询"],
}
__plugin_cd_limit__ = {"cd": 8}


nbnhhsh = on_command("缩写", aliases={"缩写查询"}, permission=GROUP, priority=5, block=True)
commands = {"是啥", "是什么", "是谁"}
what = on_keyword(commands, permission=GROUP, priority=5)
baike = on_command("梗百科", aliases={"百科"}, permission=GROUP, priority=5, block=True)


# 清除cd
def clear_cd(matcher: Matcher, event: MessageEvent):
    module = matcher.plugin_name
    if plugins2cd_manager.check_plugin_cd_status(module):
        plugin_cd_data = plugins2cd_manager.get_plugin_cd_data(module)
        check_type = plugin_cd_data["check_type"]
        limit_type = plugin_cd_data["limit_type"]
        if (
            (isinstance(event, PrivateMessageEvent) and check_type == "private")
            or (isinstance(event, GroupMessageEvent) and check_type == "group")
            or plugins2cd_manager.get_plugin_data(module).get("check_type") == "all"
        ):
            cd_type_ = event.user_id
            if limit_type == "group" and isinstance(event, GroupMessageEvent):
                cd_type_ = event.group_id
            if plugins2cd_manager.get_cd_count(module, cd_type_) > 0:
                plugins2cd_manager.sub_cd_count(module, cd_type_)


@what.handle()
async def _(
        event: GroupMessageEvent,
        matcher: Matcher,
        msg: str = EventPlainText(),
        to_me: bool = EventToMe()
):
    def split_command(msg):
        for command in commands:
            if command in msg:
                prefix, suffix = re.split(command, msg, 1)
                return prefix, suffix
        return "", ""

    msg = msg.strip().strip(".>,?!。，（）()[]【】")
    prefix_words = ["这", "这个", "那", "那个", "你", "我", "他", "它", "zx"]
    suffix_words = ["意思", "梗", "玩意", "鬼"]
    prefix, suffix = split_command(msg)
    if (not prefix or prefix in prefix_words) or (
        suffix and suffix not in suffix_words
    ):
        what.block = False
        clear_cd(matcher, event)
        await what.finish()
    keyword = prefix

    if to_me:
        res = await get_content(keyword)
    else:
        res = await get_content(keyword, sources=["jiki", "nbnhhsh"])

    if res:
        what.block = True
        await what.finish(res)
    else:
        what.block = False
        clear_cd(matcher, event)
        ignore_mute(f"{event.group_id}_{event.user_id}")
        await what.finish()


@baike.handle()
async def _(msg: Message = CommandArg()):
    keyword = msg.extract_plain_text().strip()
    if not keyword:
        await baike.finish()

    res = await get_content(keyword)
    if res:
        await baike.finish(res)
    else:
        await baike.finish("找不到相关的条目")


@nbnhhsh.handle()
async def _(msg: Message = CommandArg()):
    keyword = msg.extract_plain_text().strip()
    if not keyword:
        await nbnhhsh.finish("你没说话嘛！")
    if not re.fullmatch(r"[0-9a-zA-Z]+", keyword):
        await nbnhhsh.finish("要好好输入字母缩写呀！")

    res = await get_content(keyword, sources=["nbnhhsh"])
    if res:
        await nbnhhsh.finish(res)
    else:
        await nbnhhsh.finish("找不到相关的缩写")
