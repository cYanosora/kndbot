import random
import re
import time
from typing import Dict, Optional, List, Union

import requests
import yaml
from PIL import ImageDraw, Image, ImageFont
from nonebot import on_command, get_driver
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message, MessageEvent, ActionFailed
from configs.path_config import FONT_PATH
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from utils.utils import scheduler, is_number, get_message_at
from services import logger
from .._autoask import pjsk_update_manager
from .._errors import apiCallError, maintenanceIn, userIdBan
from .._utils import currentevent, getEventId, near_rank, getUserData, callapi
from .._models import PjskBind
from .._config import *
import json
driver = get_driver()

__plugin_name__ = "活动查分/sk"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    pjsk活动查分，仅限日服
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，一分钟内每人最多查询3次
    因为sbga的原因，今后只能查前百的分数
    指令：
        sk [排名]               查询此排名玩家的活动分数，仅限前百
        sk *[多个排名]            查询给出的排名玩家的活动分数，排名用空格隔开，仅限前百
        sk [id]                 查询此id玩家的活动分数，仅限前百
        sk @qq                  查看艾特用户的活动分数(对方必须已绑定烧烤账户且排名前百) 
        sk                      查询自己的活动分数，仅限前百
        sk预测/活动预测/ycx        查看烧烤当前日服活动预测线
        5v5人数                  查看当前5v5活动的两队人数
    数据来源：
        pjsekai.moe
        unipjsk.com
        3-3.dev
""".strip()
__plugin_superuser_usage__ = f"""
superuser_usage：
    pjsk活动号更新
    指令：
        pjsk活动更新        手动更新当前活动号
"""
__plugin_settings__ = {
    "default_status": False,
    "cmd": ['sk', "活动查分", "烧烤相关"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 3, "rst": "别急，你才刚查完呢", "limit_type": "user"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# pjsk查分
pjsk_sk = on_command('sk', priority=5, block=True)

# pjsk活动号更新
pjsk_event_update = on_command('pjsk活动更新', permission=SUPERUSER, priority=1, block=True)

# pjsk榜线查询
pjsk_pred_query = on_command('sk预测', aliases={"活动预测", 'ycx'}, priority=4, block=True)

# pjsk 5v5人数查询
pjsk_5v5_query = on_command('5v5人数', priority=5, block=True)


@pjsk_sk.handle()
async def _(matcher: Matcher, event: MessageEvent, msg: Message = CommandArg()):
    # 获取活动号，预测线
    global pred_score_json
    # 初始化活动号
    event_data = currentevent()
    # 初始化预测线
    if not pred_score_json.get('data'):
        await pjsk_pred_update()
    if event_data.get('status', 'going') == 'counting':
        await pjsk_sk.finish('活动分数统计中，不要着急哦！', at_sender=True)
    # 处理用户参数
    ranks = None
    arg = re.sub(r'\D', " ", msg.extract_plain_text().strip())
    if all(i.isdigit() for i in arg.split()):
        ranks = [i.strip() for i in arg.split()]
    else:
        arg = arg.replace(" ", "")
    isprivate = False
    # 输入的参数并不是多个排名
    if not ranks or len(ranks) == 1:
        # 若无参数，尝试获取用户绑定的id
        if not arg:
            qq_ls = get_message_at(event.raw_message)
            qid = qq_ls[0] if qq_ls and qq_ls[0] != event.self_id else event.user_id
            arg, isprivate = await PjskBind.get_user_bind(qid)
            if not arg:
                await pjsk_sk.finish(
                    f"{'你' if event.user_id == qid else '用户'}还没有绑定哦",
                    at_sender=True
                )
            if isprivate and qid != event.user_id:
                await pjsk_sk.finish("查不到捏，可能是不给看", at_sender=True)
            param = {'targetUserId': arg}
        # 若有参数，区别处理
        # 输入的是用户id或者排名
        elif arg.isdigit():
            search_type = 'targetUserId' if len(arg) > 8 else 'targetRank'
            param = {search_type: arg}
        # 若获取玩家信息失败
        else:
            await pjsk_sk.finish("你这ID有问题啊", at_sender=True)
            return
    # 输入的参数是多个排名
    else:
        param = {'targetRank': ranks}
        isprivate = True
    await send_msg(matcher, param, isprivate, event_data)


async def send_msg(
    matcher: Matcher,
    param: Dict[str, Union[str, List[str]]],
    isprivate: bool,
    event_data: Optional[Dict] = None
):
    global event_id
    if event_data is None:
        event_data = currentevent()
    event_id = event_data["id"] if int(event_data["id"]) > event_id else event_id
    url_list = [i + '/user/{user_id}/event/' + str(event_id) + '/ranking' for i in api_base_url_list]
    # 单排名图片
    is_simple = any(isinstance(i, List) for i in param.values())
    if not is_simple:
        # 获取自己排名信息
        try:
            url = random.choice(url_list)
            userdata = await getUserData(url, param)
            myid = userdata['id']
            myname = userdata['name']
            myscore = userdata['score']
            myrank = userdata['rank']
            myteaminfo = userdata['teaminfo']
            assetbundleName = userdata['assetbundleName']
        except IndexError:
            await matcher.finish('查不到数据捏，可能这期活动没打', at_sender=True)
            return
        except (maintenanceIn, apiCallError, userIdBan) as e:
            await matcher.finish(str(e), at_sender=True)
            return
        except Exception as e:
            await matcher.finish(BUG_ERROR, at_sender=True)
            logger.warning(f"pjsk查分失败。Error：{e}")
            return
        # 制作排名图片
        img = Image.new('RGB', (600, 600), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 25)
        if not isprivate:
            myid = f' - {myid}'
        else:
            myid = ''
        pos = 20
        draw.text((20, pos), myname + myid, '#000000', font)
        pos += 35
        # 添加5v5队伍信息
        if myteaminfo:
            try:
                team = await pjsk_update_manager.get_asset(
                    f'ondemand/event/{event_data["assetbundleName"]}/team_image', f'{assetbundleName}.png',
                    block=True
                )
                team = team.resize((45, 45))
                r, g, b, mask = team.split()
                img.paste(team, (20, 63), mask)
                team_pos = (70, 65)
            except AttributeError:
                team_pos = (20, 65)
                pass
            draw.text(
                team_pos,
                myteaminfo[0] + ('(' + myteaminfo[1] + ')' if myteaminfo[1] else ''),
                '#000000',
                font
            )
            pos += 50
        # 添加自己排名信息
        font2 = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 38)
        draw.text((20, pos), f'分数{myscore / 10000}W，排名{myrank}', '#000000', font2)
        pos += 60
        # 获取附近排名信息
        mynear_rank = near_rank(myrank)
        try:
            for eachrank in mynear_rank:
                try:
                    url = random.choice(url_list)
                    param = {'targetRank': eachrank['rank']}
                    user_data = await getUserData(url, param)
                    score = user_data['score']
                    deviation = abs(score - myscore) / 10000
                    draw.text(
                        (20, pos),
                        f'{eachrank["rank"]}名分数 {score / 10000}W  '
                        f'{eachrank["tag"]}{deviation}W ',
                        '#000000',
                        font
                    )
                    pos += 38
                except:
                    pass
        except Exception as e:
            logger.warning(f'获取附近排名玩家信息错误，Error:{e}')
            pass
        pos += 10
        # 补充预测线数据&活动剩余时间
        if event_data['status'] == 'going':
            # 补充预测线数据
            if pred_score_json['id'] == event_id:
                for eachrank in mynear_rank:
                    if pred_score_json['id'] == event_id and event_data['status'] == 'going':
                        pred = pred_score_json['data'].get(str(eachrank['rank']))
                    else:
                        pred = None
                    if pred:
                        draw.text(
                            (20, pos),
                            f'{eachrank["rank"]}名 预测{pred / 10000}W',
                            '#000000',
                            font
                        )
                        pos += 38
                font3 = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 16)
                draw.text((400, pos + 49), '预测线来自33（3-3.dev）', (150, 150, 150), font3)
            # 活动剩余时间
            if event_data["id"] == event_id:
                draw.text((20, pos), '活动还剩' + event_data['remain'], '#000000', font)
        pos += 38
        draw.text((20, pos), f'数据生成于{userdata["updateTime"]}', '#000000', font)
        # 发送排名图片
        img = img.crop((0, 0, 600, pos + 58))
        await matcher.finish(image(b64=pic2b64(img)))
    # 多排名图片
    else:
        result = ''
        updateTime = ''
        for q in param.keys():
            for userid in param[q]:
                try:
                    url = random.choice(url_list)
                    userdata = await getUserData(url, {q: userid})
                    userId = userdata['id']
                    name = userdata['name']
                    score = userdata['score']
                    rank = userdata['rank']
                    teaminfo = userdata['teaminfo']
                    updateTime = updateTime if updateTime else f'数据生成于{userdata["updateTime"]}'
                    teamname = teaminfo[1] or teaminfo[0] if teaminfo else ''
                except Exception:
                    continue
                else:
                    msg = f'{name} - {userId}\n{teamname}分数{score / 10000}W，排名{rank}'
                    result += f'{msg}\n\n'
        if result:
            result = result[:-1] + updateTime
            try:
                await matcher.finish(result[:-2])
            except ActionFailed:
                await matcher.finish(image(b64=pic2b64(text2image(result[:-2]))))
        else:
            await matcher.finish(BUG_ERROR + '\n查分仅支持前百！')


@pjsk_event_update.handle()
async def _(msg: Message = CommandArg()):
    global pred_score_json
    global event_id
    arg = msg.extract_plain_text().strip()
    if is_number(arg):
        event_id = int(arg)
        await pjsk_event_update.finish(f"pjsk更新活动号成功，当前活动号{event_id}", at_sender=True)
        return
    else:
        try:
            tmp_id = (await getEventId(current_event_url_bak))['eventId']
            event_id = int(tmp_id) if int(tmp_id) > event_id else event_id
            await pjsk_event_update.send(f"pjsk更新活动号成功，当前活动号{event_id}", at_sender=True)
        except:
            await pjsk_event_update.send(f"pjsk更新活动号失败，使用默认id号{event_id}", at_sender=True)
    try:
        resp = requests.get(pred_url, headers=headers)
        tmp_json = resp.json()
        if tmp_json["status"] == "success":
            pred_score_json = {
                "data": tmp_json["data"],
                "time": tmp_json["data"]["ts"]/1000,
                "id": tmp_json["data"]["eventId"]
            }
        logger.info("pjsk更新预测线成功！")
    except Exception as e:
        logger.warning(f"pjsk更新预测线失败！Error:{e}")


async def pjsk_pred_update():
    global pred_score_json
    global event_id
    resp_text = ""
    try:
        # 因为AsyncHttpx封装的异步httpx处理不了跳转url，所以此处只能用阻塞式网络请求orz
        resp = requests.get(pred_url, headers=headers)
        tmp_json = resp.json()
        if tmp_json["status"] == "success" and tmp_json["event"]["id"] == event_id:
            pred_score_json = {
                "data": tmp_json["data"],
                "time": tmp_json["data"]["ts"] / 1000,
                "id": event_id
            }
            resp_data = pred_score_json["data"]
            for rank, score in resp_data.items():
                if is_number(rank):
                    resp_text += "{}名预测：{}\n".format(rank, format(score, ','))
            if resp_data:
                resp_text += '\n预测数据来自 3-3.dev\n'
                resp_text += '由于服务器限制，预测误差极大，请谨慎参考！\n'
        elif tmp_json["status"] == "success" and tmp_json["data"]["eventId"] < event_id:
            resp_text = '预测暂不可用'
        logger.info("pjsk更新预测线成功！")
    except Exception as e:
        if pred_score_json["id"] == event_id:
            resp_data = pred_score_json["data"]
            for rank, score in resp_data.items():
                if is_number(rank):
                    resp_text += "{}名预测：{}\n".format(rank, format(score, ','))
            if resp_data and int(time.time()) - 60 * 30 > pred_score_json["time"]:
                yctime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(pred_score_json["time"]))
                resp_text += f'预测线生成时间{yctime}\n'
            if resp_data:
                resp_text += '\n预测数据来自 3-3.dev\n'
                resp_text += '由于服务器限制，预测误差极大，请谨慎参考！\n'
        logger.warning(f"pjsk更新预测线失败！Error:{e}")
    return resp_text


@pjsk_pred_query.handle()
async def _():
    reply = await pjsk_pred_update()
    if reply:
        await pjsk_pred_query.finish(
            image(b64=pic2b64(text2image(reply, fontsize=25, padding=(20, 10))))
        )
    else:
        await pjsk_pred_query.finish(BUG_ERROR)


@pjsk_5v5_query.handle()
async def _():
    reply = await pjsk_cheer_pred_update()
    if reply:
        await pjsk_pred_query.finish(
            image(b64=pic2b64(text2image(reply, fontsize=25, padding=(20, 10))))
        )
    else:
        await pjsk_pred_query.finish(BUG_ERROR)


async def pjsk_cheer_pred_update():
    global event_id
    resp_text = ""
    try:
        resp = requests.get(cheer_pred_url)
        data = resp.json()
        if data['eventId'] != event_id:
            return None
        with open(data_path / 'cheerfulCarnivalTeams.json', 'r', encoding='utf-8') as f:
            Teams = json.load(f)
        with open(data_path / 'translate.yaml', encoding='utf-8') as f:
            trans = yaml.load(f, Loader=yaml.FullLoader)
        Teams.reverse()
        for TeamId in data["members"]:
            TeamRates = data['predictRates'].get(TeamId)
            TeamName = data["names"].get(TeamId)
            memberCount = data["members"][TeamId]
            try:
                translate = f"({trans['cheerful_carnival_teams'][int(TeamId)]})"
            except KeyError:
                translate = ''
            if not TeamName:
                for i in Teams:
                    if i['id'] == int(TeamId):
                        TeamName = i['teamName']
                        break
            resp_text += f"{TeamName}{translate} {memberCount}人"
            resp_text += f' 预测胜率: {TeamRates*100:.3f}%\n' if TeamRates is not None else '\n'
        return resp_text[:-1]
    except Exception as e:
        logger.warning(f"pjsk查询5v5人数失败！Error:{e}")
        return None


# 自动更新预测线
@scheduler.scheduled_job(
    "interval",
    hours=1
)
async def _():
    global pred_score_json
    try:
        # 因为AsyncHttpx封装的异步httpx处理不了跳转url，所以此处只能用阻塞式网络请求orz
        resp = requests.get(pred_url, headers=headers)
        tmp_json = resp.json()
        if tmp_json["status"] == "success":
            pred_score_json = {
                "data": tmp_json["data"],
                "time": tmp_json["data"]["ts"]/1000,
                "id": tmp_json["data"]["eventId"]
            }
        logger.info("pjsk更新预测线成功！")
    except Exception as e:
        logger.warning(f"pjsk更新预测线失败！Error:{e}")


# 自动更新活动号
@scheduler.scheduled_job(
    "cron",
    hour=14,
    minute=3
)
async def _():
    global event_id
    try:
        tmp_id = (await getEventId(current_event_url_bak))['eventId']
        event_id = int(tmp_id) if int(tmp_id) > int(event_id) else event_id
        logger.info(f"pjsk更新活动号成功，当前活动号: {event_id}！")
    except Exception as e:
        logger.warning(f"pjsk更新活动号失败！Error:{e}")


# 自动更新前百分数
@scheduler.scheduled_job(
    "interval",
    minutes=30
)
async def _():
    global event_id
    try:
        tmp_id = (await getEventId(current_event_url_bak))['eventId']
        event_id = int(tmp_id) if int(tmp_id) > int(event_id) else event_id
        url_list = [i + '/user/{user_id}/event/' + str(tmp_id) + '/ranking' for i in api_base_url_list]
        url = random.choice(url_list) + '?rankingViewType=top100'
        ranking = await callapi(url)
        with open(data_path / 'sktop100.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(ranking, sort_keys=True, indent=4))
        logger.info(f"pjsk更新前百活动分数成功！")
    except Exception as e:
        logger.warning(f"pjsk更新前百活动分数失败！Error:{e}")
