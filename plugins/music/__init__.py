from typing import Tuple, Any
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP
from nonebot.params import RegexGroup
from services.log import logger
from nonebot import on_regex
from .music_163 import sources, Source
from utils.limit_utils import ignore_cd,ignore_count
from nonebot.internal.matcher import Matcher

__plugin_name__ = "点歌"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    在线点歌
    默认为网易云点歌
    指令：
        点歌/qq点歌/网易点歌/b站点歌 [歌名]
""".strip()
__plugin_settings__ = {
    "cmd": ["点歌"],
}
__plugin_cd_limit__ = {"cd": 10, "rst": "别急，[cd]s后再用！[at]",}
__plugin_count_limit__ = {
    "max_count": 30,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再继续呢[at]",
}
music_handler = on_regex("(.*)点歌(.*)", priority=5, permission=GROUP, block=True)


@music_handler.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    if reg_group[1]:
        song = reg_group[1].strip()
        keyword = reg_group[0].strip()
        res = ""
        if not keyword:
            res = await sources[0].func(song)
        else:
            for source in sources:
                if keyword in source.keywords:
                    res = await source.func(song)
                    break
        if res:
            await music_handler.finish(res)
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id})"
                f" 点歌 {song} 成功 "
            )
        else:
            # 无结果，清除此次操作的cd，补回使用次数
            ignore_cd(matcher.plugin_name, event)
            ignore_count(matcher.plugin_name, event)
    else:
        await music_handler.finish("你没带上歌名嘛！", at_sender=True)