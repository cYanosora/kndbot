from typing import Tuple, Any
from nonebot import on_regex
from nonebot.internal.matcher import Matcher
from utils.limit_utils import ignore_cd, ignore_count
from .data_source import get_yiqing_data, get_city_and_province_list
from services.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, GROUP
from nonebot.params import  RegexGroup
from configs.config import NICKNAME
from .other_than import get_other_data

__plugin_name__ = "疫情查询"
__plugin_type__ = "实用工具"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    全国疫情查询
    指令：
        中国/美国/英国...疫情
        [省份/城市] 疫情
    * 当省份与城市重名时，可在后添加 "市" 或 "省" *
    示例： 吉林 疫情<- [省]
    示例： 吉林市 疫情 <- [市]
""".strip()
__plugin_settings__ = {
    "cmd": ["查询疫情", "疫情", "疫情查询"],
}

__plugin_cd_limit__ = {"cd": 5, "rst": "别急，[cd]s后再用！[at]",}
__plugin_block_limit__ = {}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "咱累了，这边建议你通过百度获取最新最热呢[at]",
}

yiqing = on_regex(r"(查询)?(查)?(.*)的?疫情$", permission=GROUP, priority=5, block=True)

@yiqing.handle()
async def _(bot: Bot, matcher: Matcher, event: MessageEvent, reg_group: Tuple[Any, ...] = RegexGroup(),):
    msg = reg_group[-1].strip()
    city_and_province_list = get_city_and_province_list()
    if msg:
        if msg in city_and_province_list or msg[:-1] in city_and_province_list:
            result = await get_yiqing_data(msg)
            if result:
                await yiqing.send(result)
                logger.info(
                    f"(USER {event.user_id}, GROUP "
                    f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) 查询疫情: {msg}"
                )
            else:
                await yiqing.send(f"{NICKNAME}没有查到{msg}的疫情查询...")
                logger.info(
                    f"(USER {event.user_id}, GROUP "
                    f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) 查询疫情失败"
                )
        else:
            rely = await get_other_data(msg)
            if rely:
                await yiqing.send(rely)
                logger.info(
                    f"(USER {event.user_id}, GROUP "
                    f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) 查询疫情成功"
                )
    else:
        ignore_cd(matcher.plugin_name, event)
        ignore_count(matcher.plugin_name, event)
        await yiqing.finish('那个...不告诉我是哪个地方的话，我不知道怎么查哦...', at_sender=True)
