import random
import re
import time
import yaml
from typing import List, Dict
from PIL import Image
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from utils.http_utils import AsyncHttpx
from utils.utils import get_message_at
from ._autoask import pjsk_update_manager
from ._common_utils import timeremain, callapi
from ._config import (
    rank_levels,
    data_path,
    TIMEOUT_ERROR,
    ID_ERROR,
    REFUSED_ERROR,
    api_base_url_list
)
from ._models import PjskBind
try:
    import ujson as json
except:
    import json


# 烧烤uid预处理
async def get_userid_preprocess(event: MessageEvent, msg: Message = CommandArg()):
    arg = re.sub(r'\D', "", msg.extract_plain_text().strip())
    reply = ""
    isprivate = False
    if not arg:
        qq_ls = get_message_at(event.raw_message)
        qid = qq_ls[0] if qq_ls and qq_ls[0] != event.self_id else event.user_id
        arg, isprivate = await PjskBind.get_user_bind(qid)
        if not arg:
            reply = f"{'你' if event.user_id == qid else '用户'}还没有绑定哦",
        if isprivate and qid != event.user_id:
            reply = REFUSED_ERROR
    elif arg.isdigit() and verifyid(arg):
        pass
    elif arg.isdigit() and int(arg) < 10000000:
        eventid = currentevent()['id']
        try:
            resp = await AsyncHttpx.get(
                f'{random.choice(api_base_url_list)}/user/%7Buser_id%7D/event/{eventid}/ranking?targetRank={arg}')
            ranking = json.loads(resp.content)
            arg = ranking['rankings'][0]['userId']
            isprivate = True
        except:
            reply = TIMEOUT_ERROR
    else:
        reply = ID_ERROR
    return {
        'error': reply,
        'private': isprivate,
        'userid': arg
    }


# 当前排位赛季
def currentrankmatch():
    with open(data_path / 'rankMatchSeasons.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    for i in range(0, len(data)):
        startAt = data[i]['startAt']
        endAt = data[i]['closedAt']
        now = int(round(time.time() * 1000))
        if not startAt < now < endAt:
            continue
        return data[i]['id']
    return data[len(data) - 1]['id']


# 当期活动
def currentevent() -> dict:
    try:
        with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        for i in range(0, len(data)):
            startAt = data[i]['startAt']
            endAt = data[i]['closedAt']
            assetbundleName = data[i]['assetbundleName']
            now = int(round(time.time() * 1000))
            remain = ''
            if not startAt < now < endAt:
                continue
            if data[i]['startAt'] < now < data[i]['aggregateAt']:
                status = 'going'
                remain = timeremain((data[i]['aggregateAt'] - now) / 1000)
            elif data[i]['aggregateAt'] < now < data[i]['aggregateAt'] + 600000:
                status = 'counting'
            else:
                status = 'end'
            return {'id': data[i]['id'], 'status': status, 'remain': remain, 'assetbundleName': assetbundleName}
        return {'id': 0, 'status': 'end', 'remain': '0', 'assetbundleName': ''}
    except:
        return {'id': 0, 'status': 'end', 'remain': '0', 'assetbundleName': ''}


# 获取烧烤uid创建时间
def gettime(userid: str) -> int:
    try:
        passtime = int(userid[:-3]) / 1024 / 4096
    except ValueError:
        return 0
    return 1600218000 + int(passtime)


# 判断烧烤id是否合规
def verifyid(userid: str) -> bool:
    registertime = gettime(userid)
    now = int(time.time())
    if registertime <= 1601438400 or registertime >= now:
        return False
    else:
        return True


# 获取排名附近的档线信息
def near_rank(rank: int) -> List:
    tmp = []
    if rank == rank_levels[0]:
        return [{'tag': '↓', 'index': 1, 'rank': rank_levels[1]}]
    if rank >= rank_levels[-1]:
        return [{'tag': '↑', 'index': len(rank_levels) - 1, 'rank': rank_levels[-1]}]
    for i in range(len(rank_levels)):
        if rank <= rank_levels[i]:
            tmp.append({'tag': '↑', 'index': i - 1, 'rank': rank_levels[i - 1]})
            if rank == rank_levels[i]:
                tmp.append({'tag': '↓', 'index': i + 1, 'rank': rank_levels[i + 1]})
            else:
                tmp.append({'tag': '↓', 'index': i, 'rank': rank_levels[i]})
            break
    return tmp



# 获取用户当期活动信息
async def getUserData(url: str, param: dict) -> Dict:
    data_json = await callapi(url, param)
    result = data_json['rankings']
    userdata = {
        'id':result[0]['userId'],
        'name': result[0]['name'],
        'score': result[0]['score'],
        'rank': result[0]['rank'],
        'teaminfo': None,
        'assetbundleName': None,
        'updateTime': data_json['updateTime']
    }
    # 5v5活动额外获取队伍信息
    try:
        TeamId = result[0]['userCheerfulCarnival']['cheerfulCarnivalTeamId']
        with open(data_path / 'cheerfulCarnivalTeams.json', 'r', encoding='utf-8') as f:
            Teams = json.load(f)
        with open(data_path / 'translate.yaml', encoding='utf-8') as f:
            trans = yaml.load(f, Loader=yaml.FullLoader)
        try:
            translate = f"({trans['cheerfulCarnivalTeams'][TeamId]})"
        except KeyError:
            translate = ''
        for i in Teams:
            if i['id'] == TeamId:
                userdata['teaminfo'] = i['teamName'], translate
                userdata['assetbundleName'] = i['assetbundleName']
                break
    except:
        pass
    return userdata


# 获取活动id
async def getEventId(url: str):
    data_json = (await AsyncHttpx.get(url)).json()
    return data_json


# 生成牌子信息
async def generatehonor(honor, ismain=True):
    pic = None
    star = False
    backgroundAssetbundleName = ''
    assetbundleName = ''
    honorRarity = 0
    honorType = ''
    if honor['profileHonorType'] == 'normal':
        # 普通牌子
        with open(data_path / r'honors.json', 'r', encoding='utf-8') as f:
            honors = json.load(f)
        with open(data_path / r'honorGroups.json', 'r', encoding='utf-8') as f:
            honorGroups = json.load(f)
        for i in honors:
            if i['id'] == honor['honorId']:
                assetbundleName = i['assetbundleName']
                honorRarity = i['honorRarity']
                try:
                    star = True
                except IndexError:
                    pass
                for j in honorGroups:
                    if j['id'] == i['groupId']:
                        try:
                            backgroundAssetbundleName = j['backgroundAssetbundleName']
                        except KeyError:
                            backgroundAssetbundleName = ''
                        honorType = j['honorType']
                        break
        filename = 'honor'
        mainname = 'rank_main.png'
        subname = 'rank_sub.png'
        if honorType == 'rank_match':
            filename = 'rank_live/honor'
            mainname = 'main.png'
            subname = 'sub.png'
        # 数据读取完成
        if ismain:
            # 大图
            if honorRarity == 'low':
                frame = Image.open(data_path / r'pics/frame_degree_m_1.png')
            elif honorRarity == 'middle':
                frame = Image.open(data_path / r'pics/frame_degree_m_2.png')
            elif honorRarity == 'high':
                frame = Image.open(data_path / r'pics/frame_degree_m_3.png')
            else:
                frame = Image.open(data_path / r'pics/frame_degree_m_4.png')
            if backgroundAssetbundleName == '':
                rankpic = None
                pic = await pjsk_update_manager.get_asset(
                    rf'startapp/{filename}/{assetbundleName}', rf'degree_main.png'
                )
                try:
                    rankpic = await pjsk_update_manager.get_asset(
                        f'startapp/{filename}/{assetbundleName}', mainname
                    )
                except:
                    pass
                r, g, b, mask = frame.split()
                if honorRarity == 'low':
                    pic.paste(frame, (8, 0), mask)
                else:
                    pic.paste(frame, (0, 0), mask)
                if rankpic is not None:
                    r, g, b, mask = rankpic.split()
                    pic.paste(rankpic, (190, 0), mask)
            else:
                pic = await pjsk_update_manager.get_asset(
                    rf'startapp/{filename}/{backgroundAssetbundleName}', rf'degree_main.png'
                )
                rankpic = await pjsk_update_manager.get_asset(
                    rf'startapp/{filename}/{assetbundleName}', mainname
                )
                r, g, b, mask = frame.split()
                if honorRarity == 'low':
                    pic.paste(frame, (8, 0), mask)
                else:
                    pic.paste(frame, (0, 0), mask)
                r, g, b, mask = rankpic.split()
                pic.paste(rankpic, (190, 0), mask)
            if honorType == 'character' or honorType == 'achievement':
                if star is True:
                    honorlevel = honor['honorLevel']
                    if honorlevel > 10:
                        honorlevel = honorlevel - 10
                    if honorlevel < 5:
                        for i in range(0, honorlevel):
                            lv = Image.open(data_path / 'pics/icon_degreeLv.png')
                            r, g, b, mask = lv.split()
                            pic.paste(lv, (54 + 16 * i, 63), mask)
                    else:
                        for i in range(0, 5):
                            lv = Image.open(data_path / 'pics/icon_degreeLv.png')
                            r, g, b, mask = lv.split()
                            pic.paste(lv, (54 + 16 * i, 63), mask)
                        for i in range(0, honorlevel - 5):
                            lv = Image.open(data_path / 'pics/icon_degreeLv6.png')
                            r, g, b, mask = lv.split()
                            pic.paste(lv, (54 + 16 * i, 63), mask)
        else:
            # 小图
            if honorRarity == 'low':
                frame = Image.open(data_path / r'pics/frame_degree_s_1.png')
            elif honorRarity == 'middle':
                frame = Image.open(data_path / r'pics/frame_degree_s_2.png')
            elif honorRarity == 'high':
                frame = Image.open(data_path / r'pics/frame_degree_s_3.png')
            else:
                frame = Image.open(data_path / r'pics/frame_degree_s_4.png')
            if backgroundAssetbundleName == '':
                rankpic = None
                pic = await pjsk_update_manager.get_asset(
                    rf'startapp/{filename}/{assetbundleName}', rf'degree_sub.png'
                )
                try:
                    rankpic = await pjsk_update_manager.get_asset(
                        f'/startapp/{filename}/{assetbundleName}', subname
                    )
                except:
                    pass
                r, g, b, mask = frame.split()
                if honorRarity == 'low':
                    pic.paste(frame, (8, 0), mask)
                else:
                    pic.paste(frame, (0, 0), mask)
                if rankpic is not None:
                    r, g, b, mask = rankpic.split()
                    pic.paste(rankpic, (34, 42), mask)
            else:
                pic = await pjsk_update_manager.get_asset(
                    rf'startapp/{filename}/{backgroundAssetbundleName}', rf'degree_sub.png'
                )
                rankpic = await pjsk_update_manager.get_asset(
                    rf'startapp/{filename}/{assetbundleName}', subname
                )
                r, g, b, mask = frame.split()
                if honorRarity == 'low':
                    pic.paste(frame, (8, 0), mask)
                else:
                    pic.paste(frame, (0, 0), mask)
                r, g, b, mask = rankpic.split()
                pic.paste(rankpic, (34, 42), mask)
            if honorType == 'character' or honorType == 'achievement':
                if star is True:
                    honorlevel = honor['honorLevel']
                    if honorlevel > 10:
                        honorlevel = honorlevel - 10
                    if honorlevel < 5:
                        for i in range(0, honorlevel):
                            lv = Image.open(data_path / 'pics/icon_degreeLv.png')
                            r, g, b, mask = lv.split()
                            pic.paste(lv, (54 + 16 * i, 63), mask)
                    else:
                        for i in range(0, 5):
                            lv = Image.open(data_path / 'pics/icon_degreeLv.png')
                            r, g, b, mask = lv.split()
                            pic.paste(lv, (54 + 16 * i, 63), mask)
                        for i in range(0, honorlevel - 5):
                            lv = Image.open(data_path / 'pics/icon_degreeLv6.png')
                            r, g, b, mask = lv.split()
                            pic.paste(lv, (54 + 16 * i, 63), mask)
    elif honor['profileHonorType'] == 'bonds':
        # cp牌子
        with open(data_path / r'bondsHonors.json', 'r', encoding='utf-8') as f:
            bondsHonors = json.load(f)
            for i in bondsHonors:
                if i['id'] == honor['honorId']:
                    gameCharacterUnitId1 = i['gameCharacterUnitId1']
                    gameCharacterUnitId2 = i['gameCharacterUnitId2']
                    honorRarity = i['honorRarity']
                    break
        if ismain:
            # 大图
            if honor['bondsHonorViewType'] == 'reverse':
                pic = bondsbackground(gameCharacterUnitId2, gameCharacterUnitId1)
            else:
                pic = bondsbackground(gameCharacterUnitId1, gameCharacterUnitId2)
            chara1 = Image.open(data_path /
                                rf'chara/chr_sd_{str(gameCharacterUnitId1).zfill(2)}_01/chr_sd_'
                                rf'{str(gameCharacterUnitId1).zfill(2)}_01.png')
            chara2 = Image.open(data_path /
                                rf'chara/chr_sd_{str(gameCharacterUnitId2).zfill(2)}_01/chr_sd_'
                                rf'{str(gameCharacterUnitId2).zfill(2)}_01.png')
            if honor['bondsHonorViewType'] == 'reverse':
                chara1, chara2 = chara2, chara1
            r, g, b, mask = chara1.split()
            pic.paste(chara1, (0, -40), mask)
            r, g, b, mask = chara2.split()
            pic.paste(chara2, (220, -40), mask)
            if honorRarity == 'low':
                frame = Image.open(data_path / r'pics/frame_degree_m_1.png')
            elif honorRarity == 'middle':
                frame = Image.open(data_path / r'pics/frame_degree_m_2.png')
            elif honorRarity == 'high':
                frame = Image.open(data_path / r'pics/frame_degree_m_3.png')
            else:
                frame = Image.open(data_path / r'pics/frame_degree_m_4.png')
            r, g, b, mask = frame.split()
            if honorRarity == 'low':
                pic.paste(frame, (8, 0), mask)
            else:
                pic.paste(frame, (0, 0), mask)
            wordbundlename = f"honorname_{str(gameCharacterUnitId1).zfill(2)}" \
                             f"{str(gameCharacterUnitId2).zfill(2)}_{str(honor['bondsHonorWordId']%100).zfill(2)}_01"
            word = None
            try:
                word = await pjsk_update_manager.get_asset(
                    r'startapp/bonds_honor/word', rf'{wordbundlename}.png'
                )
            except:
                pass
            if word is not None:
                r, g, b, mask = word.split()
                pic.paste(word, (int(190-(word.size[0]/2)), int(40-(word.size[1]/2))), mask)
            if honor['honorLevel'] < 5:
                for i in range(0, honor['honorLevel']):
                    lv = Image.open(data_path / 'pics/icon_degreeLv.png')
                    r, g, b, mask = lv.split()
                    pic.paste(lv, (54 + 16 * i, 63), mask)
            else:
                for i in range(0, 5):
                    lv = Image.open(data_path / 'pics/icon_degreeLv.png')
                    r, g, b, mask = lv.split()
                    pic.paste(lv, (54 + 16 * i, 63), mask)
                for i in range(0, honor['honorLevel'] - 5):
                    lv = Image.open(data_path / 'pics/icon_degreeLv6.png')
                    r, g, b, mask = lv.split()
                    pic.paste(lv, (54 + 16 * i, 63), mask)
        else:
            # 小图
            if honor['bondsHonorViewType'] == 'reverse':
                pic = bondsbackground(gameCharacterUnitId2, gameCharacterUnitId1, False)
            else:
                pic = bondsbackground(gameCharacterUnitId1, gameCharacterUnitId2, False)
            chara1 = Image.open(data_path /
                                rf'chara/chr_sd_{str(gameCharacterUnitId1).zfill(2)}_01/chr_sd_'
                                rf'{str(gameCharacterUnitId1).zfill(2)}_01.png')
            chara2 = Image.open(data_path /
                                rf'chara/chr_sd_{str(gameCharacterUnitId2).zfill(2)}_01/chr_sd_'
                                rf'{str(gameCharacterUnitId2).zfill(2)}_01.png')
            if honor['bondsHonorViewType'] == 'reverse':
                chara1, chara2 = chara2, chara1
            chara1 = chara1.resize((120, 102))
            r, g, b, mask = chara1.split()
            pic.paste(chara1, (-5, -20), mask)
            chara2 = chara2.resize((120, 102))
            r, g, b, mask = chara2.split()
            pic.paste(chara2, (60, -20), mask)
            maskimg = Image.open(data_path / 'pics/mask_degree_sub.png')
            r, g, b, mask = maskimg.split()
            pic.putalpha(mask)
            if honorRarity == 'low':
                frame = Image.open(data_path / r'pics/frame_degree_s_1.png')
            elif honorRarity == 'middle':
                frame = Image.open(data_path / r'pics/frame_degree_s_2.png')
            elif honorRarity == 'high':
                frame = Image.open(data_path / r'pics/frame_degree_s_3.png')
            else:
                frame = Image.open(data_path / r'pics/frame_degree_s_4.png')
            r, g, b, mask = frame.split()
            if honorRarity == 'low':
                pic.paste(frame, (8, 0), mask)
            else:
                pic.paste(frame, (0, 0), mask)
            if honor['honorLevel'] < 5:
                for i in range(0, honor['honorLevel']):
                    lv = Image.open(data_path / r'pics/icon_degreeLv.png')
                    r, g, b, mask = lv.split()
                    pic.paste(lv, (54 + 16 * i, 63), mask)
            else:
                for i in range(0, 5):
                    lv = Image.open(data_path / r'pics/icon_degreeLv.png')
                    r, g, b, mask = lv.split()
                    pic.paste(lv, (54 + 16 * i, 63), mask)
                for i in range(0, honor['honorLevel'] - 5):
                    lv = Image.open(data_path / r'pics/icon_degreeLv6.png')
                    r, g, b, mask = lv.split()
                    pic.paste(lv, (54 + 16 * i, 63), mask)
    return pic


# 牌子背景图
def bondsbackground(chara1, chara2, ismain=True):
    if ismain:
        pic1 = Image.open(data_path / rf'bonds/{str(chara1)}.png')
        pic2 = Image.open(data_path / rf'bonds/{str(chara2)}.png')
        pic2 = pic2.crop((190, 0, 380, 80))
        pic1.paste(pic2, (190, 0))
    else:
        pic1 = Image.open(data_path / rf'bonds/{str(chara1)}_sub.png')
        pic2 = Image.open(data_path / rf'bonds/{str(chara2)}_sub.png')
        pic2 = pic2.crop((90, 0, 380, 80))
        pic1.paste(pic2, (90, 0))
    return pic1


