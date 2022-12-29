import re
from nonebot.adapters.onebot.v11 import Message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot import on_regex, logger
from nonebot.adapters import Event
from manager import Config
from services.log import logger
from .analysis_bilibili import b23_extract, bili_keyword

__plugin_name__ = "b站转发解析 [Hidden]"
__plugin_task__ = {"bilibili_parse": "b站转发解析"}


Config.add_plugin_config(
    "_task",
    "DEFAULT_BILIBILI_PARSE",
    True,
    help_="被动 b站转发解析 进群默认开关状态",
    default_value=True,
)
Config.add_plugin_config(
    "bili_parse",
    "ANALYSIS_BLACKLIST",
    ["3200971578"],
    help_="b站解析黑名单qq",
    default_value=["3200971578"],
)

blacklist = Config.get_config("bili_parse", "analysis_blacklist", [])

analysis_bili = on_regex(
    r"(b23.tv)|(bili(22|23|33|2233).cn)|(.bilibili.com)|(^(av|cv)(\d+))|(^BV([a-zA-Z0-9]{10})+)|"
    r"(\[\[QQ小程序\]哔哩哔哩\])|(QQ小程序&amp;#93;哔哩哔哩)|(QQ小程序&#93;哔哩哔哩)",
    flags=re.I,
    priority=1,
    permission=GROUP,
    block=False
)


@analysis_bili.handle()
async def analysis_main(event: Event) -> None:
    global blacklist
    text = str(event.get_message()).strip()
    if blacklist and event.get_user_id() in blacklist:
        logger.warning(f"User {event.get_user_id()} 处于黑名单，取消b站转发解析！")
        return
    if re.search(r"(b23.tv)|(bili(22|23|33|2233).cn)", text, re.I):
        # 提前处理短链接，避免解析到其他的
        text = await b23_extract(text)
    if hasattr(event, "group_id"):
        group_id = event.group_id
    elif hasattr(event, "channel_id"):
        group_id = event.channel_id
    else:
        group_id = None
    msg = await bili_keyword(group_id, text)
    if msg:
        await analysis_bili.finish("[[_task|bilibili_parse]]"+Message(msg))
