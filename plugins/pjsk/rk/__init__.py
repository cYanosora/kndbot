import random
import re
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageEvent, ActionFailed
from utils.http_utils import AsyncHttpx
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from utils.utils import get_message_at
from .._utils import currentrankmatch
from .._models import PjskBind
from .._config import *
try:
    import ujson as json
except:
    import json

__plugin_name__ = "排位查询/rk"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    pjsk排位查询，仅限日服
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询2次
    指令：
        rk [排名]          查询此排名玩家的排位成绩
        rk [id]           查询此id玩家的排位成绩
        rk @qq            查看艾特用户的排位成绩(对方必须已绑定烧烤账户) 
        rk                查询自己的排位成绩
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["rk", "排位查询", "烧烤相关"],
}
__plugin_cd_limit__ = {"cd": 15, "rst": "别急，你才刚查完呢", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# pjsk查排位
pjsk_rk = on_command('rk', priority=5, block=True)


@pjsk_rk.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    rankmatchid = currentrankmatch()
    url_list = [i + '/user/{user_id}/rank-match-season/' + str(rankmatchid) + '/ranking' for i in api_base_url_list]
    arg = re.sub(r'\D', "", msg.extract_plain_text().strip())
    # 若无参数，尝试获取用户绑定的id
    if not arg:
        qq_ls = get_message_at(event.raw_message)
        qid = qq_ls[0] if qq_ls and qq_ls[0] != event.self_id else event.user_id
        arg, isprivate = await PjskBind.get_user_bind(qid)
        if not arg:
            await pjsk_rk.finish(
                f"{'你' if event.user_id == qid else '用户'}还没有绑定哦",
                at_sender=True
            )
        if isprivate and qid != event.user_id:
            await pjsk_rk.finish("查不到捏，可能是不给看", at_sender=True)
        param = {'targetUserId': arg}
    # 若有参数，区别处理
    # 输入的是用户id或者排名
    elif arg.isdigit():
        search_type = 'targetUserId' if len(arg) > 8 else 'targetRank'
        param = {search_type: arg}
    # 若获取玩家信息失败
    else:
        await pjsk_rk.finish("你这ID有问题啊", at_sender=True)
        return
    data = (await AsyncHttpx.get(url=random.choice(url_list), params=param)).json()
    try:
        ranking = data['rankings'][0]['userRankMatchSeason']
        grade = int((ranking['rankMatchTierId'] - 1) / 4) + 1
    except IndexError:
        await pjsk_rk.finish('未参加当期排位赛', at_sender=True)
        return
    if grade > 7:
        grade = 7
    gradename = rankmatchgrades[grade]
    kurasu = ranking['rankMatchTierId'] - 4 * (grade - 1)
    if not kurasu:
        kurasu = 4
    winrate = ranking['winCount'] / (ranking['winCount'] + ranking['loseCount'])
    text = ''
    if grade == 7:
        text += f"{gradename}🎵×{ranking['tierPoint']}\n排名：{data['rankings'][0]['rank']}\n"
    else:
        text += f"{gradename}Class {kurasu}({ranking['tierPoint']}/5)\n排名：{data['rankings'][0]['rank']}\n"
    text += f"Win {ranking['winCount']} | Draw {ranking['drawCount']} | "
    if ranking['penaltyCount'] == 0:
        text += f"Lose {ranking['loseCount']}\n"
    else:
        text += f"Lose {ranking['loseCount'] - ranking['penaltyCount']}+{ranking['penaltyCount']}\n"
    text += f'胜率(除去平局)：{round(winrate * 100, 2)}%\n'
    text += f"最高连胜：{ranking['maxConsecutiveWinCount']}\n"
    try:
        await pjsk_rk.finish("\n" + text, at_sender=True)
    except ActionFailed:
        await pjsk_rk.finish(
            image(b64=pic2b64(text2image(text))),
            at_sender=True
        )
