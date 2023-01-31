import random
import re
import time
import requests
import yaml
from PIL import ImageDraw, Image, ImageFont
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP, Message, MessageEvent
from configs.path_config import FONT_PATH
from utils.http_utils import AsyncHttpx
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from utils.utils import scheduler, is_number, get_message_at
from services import logger
from .._autoask import pjsk_update_manager
from .._utils import currentevent, getEventId, near_rank, getUserData
from .._models import PjskBind
from .._config import *
import json

__plugin_name__ = "活动查分/sk"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    pjsk活动查分，仅限日服
    指令：
        sk [排名]                查询此排名玩家的活动分数
        sk [id]                 查询此id玩家的活动分数
        sk @qq                  查看艾特用户的活动分数(对方必须已绑定烧烤账户) 
        sk                      查询自己的活动分数
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
__plugin_cd_limit__ = {"cd": 15, "rst": "别急，你才刚查完呢", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# pjsk查分
pjsk_sk = on_command('sk', permission=GROUP, priority=5, block=True)

# pjsk活动号更新
pjsk_event_update = on_command('pjsk活动更新', permission=SUPERUSER, priority=1, block=True)

# pjsk榜线查询
pjsk_pred_query = on_command('sk预测', aliases={"活动预测", 'ycx'}, permission=GROUP, priority=4, block=True)

# pjsk 5v5人数查询
pjsk_5v5_query = on_command('5v5人数', permission=GROUP, priority=5, block=True)


@pjsk_sk.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    # 获取活动号，预测线
    global pred_score_json
    global event_id
    # 初始化活动号
    event_data = currentevent()
    # print('event_data:', event_data)
    # print('event_id:', event_id)
    event_id = event_data["id"] if int(event_data["id"]) > event_id else event_id
    # 初始化预测线
    if not pred_score_json.get('data'):
        await pjsk_pred_update()
    url_list = [i + '/user/{user_id}/event/' + str(event_id) + '/ranking' for i in api_base_url_list]
    if event_data.get('status', 'going') == 'counting':
        await pjsk_sk.finish('活动分数统计中，不要着急哦！', at_sender=True)
    # 处理用户参数
    arg = re.sub(r'\D', "", msg.extract_plain_text().strip())
    isprivate = False
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
        await pjsk_sk.finish('查不到数据捏，可能这期活动没打', at_sender=True)
        return
    except Exception as e:
        await pjsk_sk.finish('出错了，可能是bot网不好', at_sender=True)
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
                f'ondemand/event/{event_data["assetbundleName"]}/team_image', f'{assetbundleName}.png', block=True
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
            myteaminfo[0] + ('('+myteaminfo[1]+')' if myteaminfo[1] else ''),
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
                user_data = json.loads((await AsyncHttpx.get(url, params=param)).text)
                score = user_data['rankings'][0]['score']
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
            draw.text((400, pos + 11), '预测线来自33（3-3.dev）', (150, 150, 150), font3)
        # 活动剩余时间
        if event_data["id"] == event_id:
            draw.text((20, pos), '活动还剩' + event_data['remain'], '#000000', font)
            pos += 38
    # 发送排名图片
    img = img.crop((0, 0, 600, pos + 20))
    await pjsk_sk.finish(image(b64=pic2b64(img)))


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
        if tmp_json["status"] == "success" and tmp_json["data"]["eventId"] == event_id:
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
        await pjsk_pred_query.finish("活动预测线获取出错了(>︿ <。'')")


@pjsk_5v5_query.handle()
async def _():
    reply = await pjsk_cheer_pred_update()
    if reply:
        await pjsk_pred_query.finish(
            image(b64=pic2b64(text2image(reply, fontsize=25, padding=(20, 10))))
        )
    else:
        await pjsk_pred_query.finish("5v5人数获取出错了(>︿ <。'')")


async def pjsk_cheer_pred_update():
    global event_id
    url = cheer_pred_url_bak + fr'/{event_id}'
    resp_text = ""
    try:
        resp = await AsyncHttpx.get(url, headers=headers)
        data = resp.json()
        # 因为AsyncHttpx封装的异步httpx处理不了跳转url，所以此处只能用阻塞式网络请求orz
        resp = requests.get(cheer_pred_url, headers=headers)
        other_data = resp.json()

        with open(data_path / 'cheerfulCarnivalTeams.json', 'r', encoding='utf-8') as f:
            Teams = json.load(f)
        with open(data_path / 'translate.yaml', encoding='utf-8') as f:
            trans = yaml.load(f, Loader=yaml.FullLoader)
        for each_team in data["cheerfulCarnivalTeamMemberCounts"]:
            TeamId = each_team["cheerfulCarnivalTeamId"]
            memberCount = each_team["memberCount"]
            TeamRates = None
            for each_TeamId in other_data['teams']:
                if TeamId == each_TeamId:
                    TeamRates = other_data['predictRates'][str(TeamId)]
                    break
            try:
                translate = f"({trans['cheerful_carnival_teams'][TeamId]})"
            except KeyError:
                translate = ''
            for i in Teams:
                if i['id'] == TeamId:
                    resp_text += i['teamName'] + translate + " " + str(memberCount) + '人'
                    if TeamRates is not None:
                        resp_text += f' 预测胜率: {TeamRates*100:.3f}%\n'
                    else:
                        resp_text += '\n'
                    break
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

