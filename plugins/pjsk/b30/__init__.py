import random
import time
import requests
import json
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from configs.path_config import FONT_PATH
from utils.http_utils import AsyncHttpx
from utils.imageutils import pic2b64, text2image
from utils.message_builder import image
from .._autoask import pjsk_update_manager
from .._song_utils import idtoname
from .._utils import generatehonor, get_userid_preprocess
from .._config import data_path, api_base_url_list, TIMEOUT_ERROR, NOT_IMAGE_ERROR, BUG_ERROR

__plugin_name__ = "烧烤b30/pjskb30"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤b30(仅供娱乐)
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询2次
    指令：
        烧烤b30/pjsk b30               :查看自己的b30
        烧烤b30/pjsk b30  @qq          :查看艾特用户的b30(对方必须已绑定烧烤账户)
        烧烤b30/pjsk b30  烧烤id        :查看对应烧烤账号的b30
        烧烤b30/pjsk b30  活动排名       :查看当期活动排名对应烧烤用户的b30
        烧烤r30/pjsk r30               :用法同上，查询最近的30次打歌记录
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["pjskb30", "烧烤相关", "uni移植", "烧烤b30"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "user"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}
# pjskb30
pjsk_b30 = on_command('pjsk b30', aliases={'pjskb30', '烧烤b30', '烧烤 b30'}, priority=5, block=True)

# pjskr30
pjsk_r30 = on_command('pjsk r30', aliases={'pjskr30', '烧烤r30', '烧烤 r30'}, priority=5, block=True)


def fcrank(playlevel, rank):
    if playlevel <= 32:
        return rank - 1.5
    else:
        return rank - 1


async def b30single(diff, musics):
    color = {
        'master': (187, 51, 238),
        'expert': (238, 67, 102),
        'hard': (254, 170, 0),
        'normal': (51, 187, 238),
        'easy': (102, 221, 17),
    }
    musictitle = ''
    for j in musics:
        if j['id'] == diff['musicId']:
            musictitle = j['title']
    pic = Image.new("RGB", (620, 240), (255, 255, 255))
    if diff['result'] == 2 or diff['result'] == 1:
        draw = ImageDraw.Draw(pic)
        font = ImageFont.truetype(str(FONT_PATH / r'YuGothicUI-Semibold.ttf'), 48)
        size = font.getsize(musictitle)
        if size[0] > 365:
            musictitle = musictitle[:int(len(musictitle) * (345 / size[0]))] + '...'
        draw.text((238, 84), musictitle, '#000000', font)
        jacket = await pjsk_update_manager.get_asset(
            'startapp/thumbnail/music_jacket', f'jacket_s_{str(diff["musicId"]).zfill(3)}.png'
        )
        jacket = jacket.resize((186, 186))
        pic.paste(jacket, (32, 28))

        draw.ellipse((5, 5, 5 + 60, 5 + 60), fill=color[diff['musicDifficulty']])
        font = ImageFont.truetype(str(FONT_PATH / r'SourceHanSansCN-Bold.otf'), 38)
        text_width = font.getsize(str(diff['playLevel']))
        text_coordinate = (int(36 - text_width[0] / 2), int(28 - text_width[1] / 2))
        draw.text(text_coordinate, str(diff['playLevel']), (255, 255, 255), font)

        draw.ellipse((242, 32, 286, 76), fill=color[diff['musicDifficulty']])
        draw.rectangle((262, 32, 334, 76), fill=color[diff['musicDifficulty']])
        draw.ellipse((312, 32, 356, 76), fill=color[diff['musicDifficulty']])
        if diff['playLevelAdjust'] != 0:
            if diff['result'] == 2:
                resultpic = Image.open(data_path / 'pics/AllPerfect.png')
                draw.text((259, 24), str(round(diff['aplevel+'], 1)), (255, 255, 255), font)
                draw.text((370, 24), '→ ' + str(round(diff['aplevel+'], 1)), (0, 0, 0), font)
            if diff['result'] == 1:
                resultpic = Image.open(data_path / 'pics/FullCombo.png')
                draw.text((259, 24), str(round(diff['fclevel+'], 1)), (255, 255, 255), font)
                draw.text((370, 24), '→ ' + str(round(fcrank(diff['playLevel'], diff["fclevel+"]), 1)), (0, 0, 0), font)
        else:
            if diff['result'] == 2:
                resultpic = Image.open(data_path / 'pics/AllPerfect.png')
                draw.text((259, 24), f'{round(diff["aplevel+"], 1)}.?', (255, 255, 255), font)
                draw.text((370, 24), f'→ {round(diff["aplevel+"], 1)}.0', (0, 0, 0), font)
            if diff['result'] == 1:
                resultpic = Image.open(data_path / 'pics/FullCombo.png')
                draw.text((259, 24), f'{round(diff["fclevel+"], 1)}.?', (255, 255, 255), font)
                draw.text((370, 24), f'→ {round(fcrank(diff["playLevel"], diff["fclevel+"]), 1)}', (0, 0, 0), font)
        r, g, b, mask = resultpic.split()
        pic.paste(resultpic, (238, 154), mask)
    pic = pic.resize((310, 120))
    return pic


@pjsk_b30.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    # 获取id
    state = await get_userid_preprocess(event, msg)
    if reply := state['error']:
        await pjsk_b30.finish(reply, at_sender=True)
    userid = state['userid']
    isprivate = state['private']
    # 获取profile
    await pjsk_b30.send("收到", at_sender=True)
    try:
        url = f'{random.choice(api_base_url_list)}/user/{userid}/profile'
        data = (await AsyncHttpx.get(url, timeout=10)).json()
    except:
        url = f'{random.choice(api_base_url_list)}/user/{userid}/profile'
        data = requests.get(url, timeout=10).json()
    if not data:
        await pjsk_b30.finish(TIMEOUT_ERROR)
        return
    # 设置文字
    name = data['user']['userGamedata']['name']
    userProfileHonors = data['userProfileHonors']
    rank = data['user']['userGamedata']['rank']
    userDecks = [0, 0, 0, 0, 0]
    special_training = [False, False, False, False, False]
    for i in range(0, 5):
        userDecks[i] = data['userDecks'][0][f'member{i + 1}']
        for userCards in data['userCards']:
            if userCards['cardId'] != userDecks[i]:
                continue
            if userCards['defaultImage'] == "special_training":
                special_training[i] = True
    pic = Image.open(data_path / 'pics/b30.png')
    id = '保密' if isprivate else userid
    # 获取卡图资源
    error_flag = True
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    try:
        assetbundleName = ''
        for i in cards:
            if i['id'] == userDecks[0]:
                assetbundleName = i['assetbundleName']
        if special_training[0]:
            cardimg = await pjsk_update_manager.get_asset(
                r'startapp/thumbnail/chara', f'{assetbundleName}_after_training.png'
            )
            cutoutimg = await pjsk_update_manager.get_asset(
                rf'startapp/character/member_cutout_trm/{assetbundleName}', 'after_training.png',
                download=False
            )
            if cutoutimg is None:
                cutoutimg = await pjsk_update_manager.get_asset(
                    rf'startapp/character/member_cutout_trm/{assetbundleName}/after_training', 'after_training.png'
                )
        else:
            cardimg = await pjsk_update_manager.get_asset(
                r'startapp/thumbnail/chara', f'{assetbundleName}_normal.png'
            )
            cutoutimg = await pjsk_update_manager.get_asset(
                f'startapp/character/member_cutout_trm/{assetbundleName}', 'normal.png',
                download=False
            )
            if cutoutimg is None:
                cutoutimg = await pjsk_update_manager.get_asset(
                    f'startapp/character/member_cutout_trm/{assetbundleName}', 'normal.png'
                )
        cutoutimg = cutoutimg.resize((int(cutoutimg.size[0] * 0.47), int(cutoutimg.size[1] * 0.47)))
        r, g, b, mask = cutoutimg.split()
        pic.paste(cutoutimg, (770, 15), mask)

        cardimg = cardimg.resize((116, 116))
        r, g, b, mask = cardimg.split()
        pic.paste(cardimg, (68, 70), mask)
    except FileNotFoundError:
        pass
    except AttributeError:
        if error_flag:
            await pjsk_b30.send(NOT_IMAGE_ERROR)
            error_flag = False
    # 合成b30图片
    draw = ImageDraw.Draw(pic)
    font_style = ImageFont.truetype(str(FONT_PATH / r"SourceHanSansCN-Bold.otf"), 35)
    draw.text((215, 65), name, fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype(str(FONT_PATH / r"FOT-RodinNTLGPro-DB.ttf"), 15)
    draw.text((218, 118), f'id:{id}', fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype(str(FONT_PATH / r"FOT-RodinNTLGPro-DB.ttf"), 28)
    draw.text((314, 150), str(rank), fill=(255, 255, 255), font=font_style)
    for i in userProfileHonors:
        try:
            if i['seq'] == 1:
                honorpic = await generatehonor(i, True)
                honorpic = honorpic.resize((226, 48))
                r, g, b, mask = honorpic.split()
                pic.paste(honorpic, (59, 226), mask)
            elif i['seq'] == 2:
                honorpic = await generatehonor(i, False)
                honorpic = honorpic.resize((107, 48))
                r, g, b, mask = honorpic.split()
                pic.paste(honorpic, (290, 226), mask)
            elif i['seq'] == 3:
                honorpic = await generatehonor(i, False)
                honorpic = honorpic.resize((107, 48))
                r, g, b, mask = honorpic.split()
                pic.paste(honorpic, (403, 226), mask)
        except AttributeError:
            if error_flag:
                await pjsk_b30.send(NOT_IMAGE_ERROR)
                error_flag = False
    # 获取b30歌曲
    with open(data_path / r'realtime/musicDifficulties.json', 'r', encoding='utf-8') as f:
        diff = json.load(f)
    for i in range(0, len(diff)):
        try:
            diff[i]['playLevelAdjust']
        except KeyError:
            diff[i]['playLevelAdjust'] = 0
            diff[i]['fullComboAdjust'] = 0
            diff[i]['fullPerfectAdjust'] = 0
    for i in range(0, len(diff)):
        diff[i]['result'] = 0
        diff[i]['rank'] = 0
        diff[i]['fclevel+'] = diff[i]['playLevel'] + diff[i]['fullComboAdjust']
        diff[i]['aplevel+'] = diff[i]['playLevel'] + diff[i]['fullPerfectAdjust']
    diff.sort(key=lambda x: x["aplevel+"], reverse=True)
    highest = 0
    for i in range(0, 30):
        highest = highest + diff[i]['aplevel+']
    highest = round(highest / 30, 2)
    with open(data_path / r'realtime/musics.json', 'r', encoding='utf-8') as f:
        musics = json.load(f)
    for music in data['userMusicResults']:
        playResult = music['playResult']
        musicId = music['musicId']
        musicDifficulty = music['musicDifficulty']
        i = 0
        found = False
        for i in range(0, len(diff)):
            if diff[i]['musicId'] == musicId and diff[i]['musicDifficulty'] == musicDifficulty:
                found = True
                break
        if found:
            if playResult == 'full_perfect':
                diff[i]['result'] = 2
                diff[i]['rank'] = diff[i]['aplevel+']
            elif playResult == 'full_combo':
                if diff[i]['result'] < 1:
                    diff[i]['result'] = 1
                    diff[i]['rank'] = fcrank(diff[i]['playLevel'], diff[i]['fclevel+'])
    diff.sort(key=lambda x: x["rank"], reverse=True)
    rank = 0
    shadow = Image.new("RGBA", (320, 130), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", (310, 120), (0, 0, 0, 50)), (5, 5))
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    # 粘贴b30歌曲图片
    for i in range(0, 30):
        rank = rank + diff[i]['rank']
        try:
            single = await b30single(diff[i], musics)
        except AttributeError:
            await pjsk_b30.finish(BUG_ERROR)
            return
        r, g, b, mask = shadow.split()
        pic.paste(shadow, ((int(52 + (i % 3) * 342)), int(307 + int(i / 3) * 142)), mask)
        pic.paste(single, ((int(53 + (i % 3) * 342)), int(309 + int(i / 3) * 142)))
    rank = round(rank / 30, 2)

    font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Medium.otf"), 16)
    draw.text((50, 1722), f'注：33+FC权重减1，其他减1.5，非官方算法，仅供参考娱乐，当前理论值为{highest}', fill='#00CCBB',
              font=font_style)
    draw.text((50, 1752), '定数来源：https://profile.pjsekai.moe/  ※定数每次统计时可能会改变', fill='#00CCBB',
              font=font_style)
    rankimg = Image.new("RGBA", (120, 55), (100, 110, 180, 0))
    draw = ImageDraw.Draw(rankimg)
    font_style = ImageFont.truetype(str(FONT_PATH / r"SourceHanSansCN-Bold.otf"), 35)
    text_width = font_style.getsize(str(rank))
    # 硬核画文字边框
    draw.text((int(60 - text_width[0] / 2) + 3, int(20 - text_width[1] / 2)), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2) - 3, int(20 - text_width[1] / 2)), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2), int(20 - text_width[1] / 2) + 3), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2), int(20 - text_width[1] / 2) - 3), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2) - 2, int(20 - text_width[1] / 2) - 2), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2) + 2, int(20 - text_width[1] / 2) + 2), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2) - 2, int(20 - text_width[1] / 2) + 2), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    draw.text((int(60 - text_width[0] / 2) + 2, int(20 - text_width[1] / 2) - 2), str(rank), fill=(61, 74, 162, 210),
              font=font_style)
    rankimg = rankimg.filter(ImageFilter.GaussianBlur(1.2))
    draw = ImageDraw.Draw(rankimg)
    draw.text(
        (int(60 - text_width[0] / 2), int(20 - text_width[1] / 2)),
        str(rank), fill=(255, 255, 255), font=font_style
    )
    r, g, b, mask = rankimg.split()
    pic.paste(rankimg, (565, 142), mask)
    pic = pic.convert("RGB")

    await pjsk_b30.finish(image(b64=pic2b64(pic)))


@pjsk_r30.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    state = await get_userid_preprocess(event, msg)
    if reply := state['error']:
        await pjsk_r30.finish(reply, at_sender=True)
    await pjsk_r30.send("收到")
    with open(data_path / 'realtime/musics.json', 'r', encoding='utf-8') as f:
        musicdata = json.load(f)
    userid = state['userid']
    isprivate = state['private']
    resp = requests.get(f'{random.choice(api_base_url_list)}/user/{userid}/profile')
    data = json.loads(resp.content)
    name = data['user']['userGamedata']['name']
    userMusicResults = data['userMusicResults']
    userMusicResults.sort(key=lambda x: x["updatedAt"], reverse=True)
    text = f'{name}\n' if isprivate else f'{name} - {userid}\n'
    for count, musics in enumerate(userMusicResults):
        timeArray = time.localtime(musics['updatedAt'] / 1000)
        otherStyleTime = time.strftime("%m-%d %H:%M", timeArray)
        text += f"{otherStyleTime}: {idtoname(musics['musicId'], musicdata)} [{musics['musicDifficulty'].upper()}] {musics['playType']}\n"
        if count == 29:
            break
    text += '由于pjsk统计机制的问题会导致统计不全'
    await pjsk_r30.finish(
        image(b64=pic2b64(text2image(text))),
        at_sender=True
    )