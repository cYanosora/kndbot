import re
from emoji.unicode_codes import UNICODE_EMOJI
from nonebot.internal.matcher import Matcher
from utils.limit_utils import ignore_count
from utils.message_builder import reply
from nonebot import on_regex
from nonebot.params import RegexDict
from nonebot.adapters.onebot.v11 import MessageSegment, GROUP, GroupMessageEvent
from .data_source import mix_emoji

__plugin_name__ = "表情合成"
__plugin_type__ = "图片类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    表情合成(不支持部分黄豆表情 以及 所有qq黄豆表情)
    指令：
        [表情1] + [表情2]
""".strip()
__plugin_settings__ = {
    "cmd": ["表情合成"],
}
__plugin_count_limit__ = {
    "max_count": 5,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再来呢",
}

emojis = filter(lambda e: len(e) == 1, UNICODE_EMOJI["en"])
pattern = "(" + "|".join(re.escape(e) for e in emojis) + ")"
emojimix = on_regex(
    rf"^\s*(?P<code1>{pattern})\s*[\+＋]\s*(?P<code2>{pattern})\s*$",
    permission=GROUP,
    block=True,
    priority=5,
)


@emojimix.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, msg: dict = RegexDict()):
    emoji_code1 = msg["code1"]
    emoji_code2 = msg["code2"]
    result = await mix_emoji(emoji_code1, emoji_code2)
    if isinstance(result, str):
        ignore_count(matcher.plugin_name, event)
        await emojimix.finish(reply(event.message_id) + result)
    else:
        await emojimix.finish(reply(event.message_id) + MessageSegment.image(result))
