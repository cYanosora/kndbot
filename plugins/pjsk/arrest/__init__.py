import json
import random
import traceback
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message, ActionFailed
from nonebot.params import CommandArg
from services import logger
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from .._errors import maintenanceIn, userIdBan, apiCallError
from .._utils import currentrankmatch, get_userid_preprocess, callapi
from .._models import UserProfile
from .._config import api_base_url_list, rankmatchgrades, BUG_ERROR, TIMEOUT_ERROR, NOT_PLAYER_ERROR

__plugin_name__ = "逮捕"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤收歌情况
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询2次
    指令：
        逮捕              :查看自己的收歌情况
        逮捕 @qq          :查看艾特用户的收歌情况(对方必须已绑定烧烤账户)
        逮捕 烧烤id        :查看对应烧烤账号的收歌情况
        逮捕 活动排名       :查看当前活动排名对应烧烤用户的收歌情况
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["逮捕", "烧烤相关", "uni移植"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "user"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}

# pjsk逮捕
pjsk_assest = on_command('逮捕', priority=5, block=True)


@pjsk_assest.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    state = await get_userid_preprocess(event, msg)
    if reply := state['error']:
        await pjsk_assest.finish(reply, at_sender=True)
    userid = state['userid']
    isprivate = state['private']
    try:
        profile = UserProfile()
        await profile.getprofile(userid)
    except (json.decoder.JSONDecodeError, IndexError):
        await pjsk_assest.finish(NOT_PLAYER_ERROR)
        return
    except (maintenanceIn, userIdBan) as e:
        await pjsk_assest.finish(str(e))
        return
    except:
        traceback.print_exc()
        await pjsk_assest.finish(BUG_ERROR)
        return
    text = f"{profile.name} - {userid}\n" if not isprivate else f"{profile.name}\n"
    text += f"expert进度:FC {profile.full_combo[3]}/{profile.clear[3]}," \
            f" AP{profile.full_perfect[3]}/{profile.clear[3]}\n" \
            f"master进度:FC {profile.full_combo[4]}/{profile.clear[4]}," \
            f" AP{profile.full_perfect[4]}/{profile.clear[4]}\n"
    ap33plus = profile.masterscore[33][0] + profile.masterscore[34][0] + profile.masterscore[35][0] + \
               profile.masterscore[36][0] + profile.masterscore[37][0]
    fc33plus = profile.masterscore[33][1] + profile.masterscore[34][1] + profile.masterscore[35][1] + \
               profile.masterscore[36][1] + profile.masterscore[37][1]
    if ap33plus != 0:
        text = text + f"\nLv.33及以上AP进度：{ap33plus}/{profile.masterscore[33][3] + profile.masterscore[34][3] + profile.masterscore[35][3] + profile.masterscore[36][3] + profile.masterscore[37][3]}"
    if fc33plus != 0:
        text = text + f"\nLv.33及以上FC进度：{fc33plus}/{profile.masterscore[33][3] + profile.masterscore[34][3] + profile.masterscore[35][3] + profile.masterscore[36][3] + profile.masterscore[37][3]}"
    if profile.masterscore[32][0] != 0:
        text = text + f"\nLv.32AP进度：{profile.masterscore[32][0]}/{profile.masterscore[32][3]}"
    if profile.masterscore[32][1] != 0:
        text = text + f"\nLv.32FC进度：{profile.masterscore[32][1]}/{profile.masterscore[32][3]}"

    # 排位数据
    rankmatchid = currentrankmatch()
    try:
        url = random.choice(api_base_url_list) + \
            f'/user/%7Buser_id%7D/rank-match-season/{rankmatchid}/ranking?targetUserId={userid}'
        data = await callapi(url)
        ranking = data['rankings'][0]['userRankMatchSeason']
        grade = int((ranking['rankMatchTierId'] - 1) / 4) + 1
        rktext = ''
        if grade > 7:
            grade = 7
        gradename = rankmatchgrades[grade]
        kurasu = ranking['rankMatchTierId'] - 4 * (grade - 1)
        if not kurasu:
            kurasu = 4
        winrate = ranking['winCount'] / (ranking['winCount'] + ranking['loseCount'])
        # 大师、其他段位荣誉称号
        if grade == 7:
            rktext += f"{gradename}🎵×{ranking['tierPoint']}\n排名：{data['rankings'][0]['rank']}\n"
        else:
            rktext += f"{gradename}Class {kurasu}({ranking['tierPoint']}/5)\n排名：{data['rankings'][0]['rank']}\n"
        # 胜负数据
        rktext += f"Win {ranking['winCount']} | Draw {ranking['drawCount']} | "
        if ranking['penaltyCount'] == 0:
            rktext += f"Lose {ranking['loseCount']}\n"
        else:
            rktext += f"Lose {ranking['loseCount'] - ranking['penaltyCount']}+{ranking['penaltyCount']}\n"
        rktext += f'胜率(除去平局)：{round(winrate * 100, 2)}%\n'
        rktext += f"最高连胜：{ranking['maxConsecutiveWinCount']}\n"
    except IndexError:
        rktext = '未参加当期排位赛'
    except (maintenanceIn, apiCallError, userIdBan) as e:
        rktext = ''
    except Exception as e:
        rktext = ''
        logger.warning(f"pjsk逮捕查排位失败。Error：{e}")
    text = text + ('\n\n' + rktext if rktext else '')
    try:
        await pjsk_assest.finish(text)
    except ActionFailed:
        await pjsk_assest.finish(image(b64=pic2b64(text2image(text))))