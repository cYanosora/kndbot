import re
from typing import Any, Tuple
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP
from nonebot.params import RegexGroup
from ._data_source import fakegacha, getcurrentgacha
from .._config import BUG_ERROR

try:
    import ujson as json
except:
    import json

__plugin_name__ = "pjsk抽卡"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    pjsk假抽卡，移植自unibot(一款功能型烧烤bot)
    由于功能容易刷屏，仅在特定群开放
    若群内已有unibot请勿开启此bot该功能
    限制每个群1分钟只能抽卡2次，每人一天只能抽10次
    指令：
        sekai抽卡/pjsk抽卡         ?[卡池id]    ：进行一次假十连
        sekai十连/pjsk十连         ?[卡池id]    ：同上
        sekai反十连/pjsk反十连      ?[卡池id]    ：四星概率翻转
        sekai[XX]连/pjsk[XX]连    ?[卡池id]    ：[XX]为数字，进行指定次数的抽卡
    注意：
        以上指令均可以携带卡池id，不携带卡池id时默认抽取当前日服最新的卡池
""".strip()
__plugin_settings__ = {
    "level": 6,
    "default_status": False,
    "cmd": ["pjsk抽卡", "sekai抽卡", "烧烤相关", "uni移植"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，抽卡正在进行中！", "limit_type": "group"}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "今天已经抽了[count]次了，还请明天再继续呢[at]",
}

# pjsk抽卡
pjsk_gacha = on_regex(r'^(?:pjsk|sekai) *(反向?)? *(抽卡|十连抽?|\d+连抽?) *(\d+)?$', permission=GROUP, priority=5, block=True)


@pjsk_gacha.handle()
async def _(reg_group: Tuple[Any, ...] = RegexGroup()):
    isreverse = True if reg_group[0] else False
    if _ := re.sub(r'\D', '', reg_group[1]):
        cardnum = int(_)
    else:
        cardnum = 10
    if cardnum > 300:
        await pjsk_gacha.finish("一次至多指定一井300抽哦", as_sender=True)
    if _ := re.sub(r'\D', '', reg_group[2] if reg_group[2] else ''):
        gachaid = int(_)
    else:
        gachaid = int(getcurrentgacha()['id'])
    try:
        result = await fakegacha(gachaid, cardnum, isreverse)
    except:
        await pjsk_gacha.finish(BUG_ERROR)
    else:
        await pjsk_gacha.finish(result)