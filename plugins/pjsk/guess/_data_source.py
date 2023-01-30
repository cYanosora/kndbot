import math
import json
import time
import random
from PIL import Image, ImageDraw
from typing import Tuple, Optional
from pathlib import Path
from mutagen.mp3 import MP3
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from pydub import AudioSegment
from configs.path_config import TEMP_PATH
# from utils.imageutils import pic2b64
# from utils.message_builder import image
from utils.message_builder import at
from ._utils import defaultVocal
from .._models import PjskGuessRank
from .._song_utils import getPlayLevel
from .._autoask import pjsk_update_manager
from .._config import data_path
from ._config import SEdir, max_tips_count, GUESS_MUSIC, GUESS_CARD
from nonebot import require
require('mappreview')
from ..mappreview._data_source import moe2img


# 随机函数
async def getRandomChart() -> Tuple[int, str]:
    """
    获取随机master谱面的musicId
    :returns: 元组形式(曲目id, 曲目名称,)
    """
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        musicdata = json.load(f)
    length = len(musicdata)
    rannum = random.randint(0, length - 1)
    while (
        musicdata[rannum]['publishedAt'] > int(time.time() * 1000)
    ):
        rannum = random.randint(0, length - 1)
    musicid = musicdata[rannum]['id']
    musicname = musicdata[rannum]['title']
    path = f'charts/moe/{musicid}'
    if not (data_path / path / 'master.jpg').exists():
        await moe2img(musicid, 'master')
    return musicid, musicname


async def getRandomJacket() -> Tuple[int, str, str]:
    """
    获取随机曲绘
    :returns: 元组形式(曲目id, 曲目名称, 曲绘asset名称)
    """
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        musicdata = json.load(f)
    length = len(musicdata)
    rannum = random.randint(0, length - 1)
    while (
        musicdata[rannum]['publishedAt'] > int(time.time() * 1000)
    ):
        rannum = random.randint(0, length - 1)
    musicid = musicdata[rannum]['id']
    musicname = musicdata[rannum]['title']
    asset = musicdata[rannum]['assetbundleName']
    path = f'startapp/music/jacket/{asset}'
    file = f'{asset}.png'
    if not (data_path / path / file).exists():
        await pjsk_update_manager.get_asset(path, file)
    return musicid, musicname, asset


async def getRandomCard() -> Tuple[int, int, str, str, str, str]:
    """
    获取随机卡面
    :returns: 元组形式(卡面id, 卡面角色id, 卡面asset名称, 卡面名称, 角色名称， 卡面稀有度)
    """
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        cardsdata = json.load(f)
    length = len(cardsdata)
    rannum = random.randint(0, length - 1)
    while (
        cardsdata[rannum]['releaseAt'] > int(time.time() * 1000)
        or cardsdata[rannum]['cardRarityType'] == 'rarity_1'
        or cardsdata[rannum]['cardRarityType'] == 'rarity_2'
    ):
        rannum = random.randint(0, length - 1)
    cardid = cardsdata[rannum]['id']
    charaid = cardsdata[rannum]['characterId']
    charaname = {
        17: '宵崎奏',18: '朝比奈真冬',19: '东云绘名',20: '晓山瑞希',
        9: '小豆泽心羽',10: '白石杏',11: '东云彰人',12: '青柳冬弥',
        5: '花里实乃理',6: '桐谷遥',7: '桃井爱莉',8: '日野森雫',
        1: '星乃一歌',2: '天马咲希',3: '望月穗波',4: '日野森志步',
        13: '天马司',14: '凤绘梦',15: '草薙宁宁',16: '神代类',
        21: '初音未来',22: '镜音铃',23: '镜音连',24: '巡音流歌',25: 'MEIKO',26: 'KAITO'
    }.get(charaid, '')
    assetbundleName = cardsdata[rannum]['assetbundleName']
    prefix = cardsdata[rannum]['prefix']
    cardRarityType = cardsdata[rannum]['cardRarityType']
    carddir = f'startapp/character/member/{assetbundleName}'
    cardfiles = ['card_normal.png'] if cardRarityType == 'rarity_birthday' else ['card_normal.png', 'card_after_training.png']
    for cardfile in cardfiles:
        if not (data_path / carddir / cardfile).exists():
            await pjsk_update_manager.get_asset(carddir, cardfile)
    return cardid, charaid, assetbundleName, charaname, prefix, cardRarityType


async def getRandomMusic() -> Tuple[int, str, str]:
    """
    获取随机曲目mp3
    :returns: 元组形式(曲目id, 曲目名称, 曲目mp3 asset名称)
    """
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        musicdata = json.load(f)
    length = len(musicdata)
    rannum = random.randint(0, len(musicdata) - 1)
    while (
        musicdata[rannum]['publishedAt'] > int(time.time() * 1000)
    ):
        rannum = random.randint(0, length - 1)

    musicid = musicdata[rannum]['id']
    musicname = musicdata[rannum]['title']
    asset = defaultVocal(musicid)
    path = f'ondemand/music/long/{asset}'
    file = f'{asset}.mp3'
    if not (data_path / path / file).exists():
        await pjsk_update_manager.get_asset(path, file)
    return musicid, musicname, asset


def update_se(musicid: int):
    """
    更新谱面SE音效文件
    """

    pass


async def getRandomSE() -> Tuple[int, str]:
    """
    获取随机谱面音效musicid
    :returns: 元组形式(曲目id, 曲目名称)
    """
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        musicdata = json.load(f)
    with open(data_path / 'musicDifficulties.json', 'r', encoding='utf-8') as f:
        musicDifficulties = json.load(f)
    length = len(musicdata)
    rannum = random.randint(0, len(musicdata) - 1)
    while (
        musicdata[rannum]['releaseAt'] > int(time.time() * 1000)
        and getPlayLevel(musicdata[rannum]['id'], 'master', musicDifficulties) < 29
    ):
        rannum = random.randint(0, length - 1)
    musicid = musicdata[rannum]['id']
    musicname = musicdata[rannum]['title']
    if not (SEdir / f'{musicid}.mp3').exists():
        update_se(musicid)
    vocal = defaultVocal(musicid)
    musicpath = data_path / f'ondemand/music/long/{vocal}/{vocal}.mp3'
    if not musicpath.exists():
        await pjsk_update_manager.get_asset(f'ondemand/music/long/{vocal}', f'{vocal}.mp3')
    return musicid, musicname


# 裁剪函数
def cutChart(musicid: int, qunnum: int) -> Tuple[Path, Path]:
    """
    裁剪谱面图片
    """
    img = Image.open(data_path / f'charts/moe/{musicid}/master.jpg')
    row = round((img.size[0] - 93.254) / 280.8)
    rannum = random.randint(2, row - 1)

    newimg = img.crop((
        int(94 + 280.8 * (rannum - 1)), 48, int(94 + 280.8 * (rannum - 1) + 190), img.size[1] - 295)
    )
    ran1 = (0, 0, 190, int(newimg.size[1] / 2) + 20)
    ran2 = (0, int(newimg.size[1] / 2) - 20, 190, newimg.size[1])
    img1 = newimg.crop(ran1)
    img2 = newimg.crop(ran2)

    final = Image.new('RGB', (410, int(img.size[1] / 2) - 10), (255, 255, 255))
    final.paste(img2, (10, 0))
    final.paste(img1, (210, -26))
    final.save(TEMP_PATH / f"map_{qunnum}.jpg", quality=60)

    ran = int(94 + 280.8 * (rannum - 1)), 48
    size = 190, img.size[1] - 295 - 48
    draw = ImageDraw.Draw(img)
    width = 5
    draw.line(
        [
            (ran[0] - width, ran[1] - width), (ran[0] + size[0] + width, ran[1] - width),
            (ran[0] + size[0] + width, ran[1] + size[1] + width),
            (ran[0] - width, ran[1] + size[1] + width), (ran[0] - width, ran[1] - width)
        ],
        fill='red', width=width
    )
    img.save(TEMP_PATH / f"map_{qunnum}_end.jpg", quality=50)
    return TEMP_PATH / f"map_{qunnum}.jpg", TEMP_PATH / f"map_{qunnum}_end.jpg"


def cutJacket(asset: str, qunnum: int, size: int = 140, isbw: bool = False) -> Tuple[Path, Path]:
    """
    裁剪曲绘图片
    """
    img = Image.open(data_path / f'startapp/music/jacket/{asset}/{asset}.png')
    img = img.convert('RGB')
    ran1 = random.randint(0, img.size[0] - size)
    ran2 = random.randint(0, img.size[1] - size)
    draw = ImageDraw.Draw(img)
    width = 3
    draw.line(
        [
            (ran1-width,ran2-width), (ran1+size+width,ran2-width), (ran1+size+width,ran2+size+width),
            (ran1-width,ran2+size+width), (ran1-width,ran2-width)
        ],
        fill='red', width=width
    )
    img.save(TEMP_PATH / f"music_{qunnum}_end.jpg", quality=50)
    img = img.crop((ran1, ran2, ran1 + size, ran2 + size))
    if isbw:
        img = img.convert("L")
    img.save(TEMP_PATH / f"music_{qunnum}.jpg", quality=60)
    return TEMP_PATH / f"music_{qunnum}.jpg", TEMP_PATH / f"music_{qunnum}_end.jpg"


def cutCard(asset: str, rarityType: str, qunnum: int, size: int = 250, isbw: bool = False) -> Tuple[Path, Path]:
    """
    裁剪卡面
    """
    if rarityType == 'rarity_birthday':
        path = data_path / f'startapp/character/member/{asset}/card_normal.png'
    else:
        if random.randint(0, 1) == 1:
            path = data_path / f'startapp/character/member/{asset}/card_after_training.png'
        else:
            path = data_path / f'startapp/character/member/{asset}/card_normal.png'
    img = Image.open(path)
    img = img.convert('RGB')
    ran1 = random.randint(0, img.size[0] - size)
    ran2 = random.randint(0, img.size[1] - size)
    draw = ImageDraw.Draw(img)
    width = 3
    draw.line(
        [
            (ran1 - width, ran2 - width), (ran1 + size + width, ran2 - width),
            (ran1 + size + width, ran2 + size + width),
            (ran1 - width, ran2 + size + width), (ran1 - width, ran2 - width)
        ],
        fill='red', width=width
    )
    img.save(TEMP_PATH / f"card_{qunnum}_end.jpg", quality=50)
    img = img.crop((ran1, ran2, ran1 + size, ran2 + size))
    if isbw:
        img = img.convert("L")
    img.save(TEMP_PATH / f"card_{qunnum}.jpg", quality=60)
    return TEMP_PATH / f"card_{qunnum}.jpg", TEMP_PATH / f"card_{qunnum}_end.jpg"


def cutMusic(assetbundleName: str, qunnum: int, reverse: bool = False) -> Tuple[Path, Path]:
    """
    裁剪歌曲mp3
    """
    path = data_path / 'ondemand/music/long'
    musicpath = path / f'{assetbundleName}/{assetbundleName}.mp3'
    length = MP3(musicpath).info.length
    music = AudioSegment.from_mp3(musicpath)
    music = music[8000:]
    music.export(TEMP_PATH / f"music_{qunnum}_end.mp3")
    starttime = random.randint(10, int(length) - 10)
    if reverse:
        cut = music[starttime * 1000: starttime * 1000 + 5000]
        cut = cut.reverse()
    else:
        cut = music[starttime * 1000: starttime * 1000 + 1700]
    cut.export(TEMP_PATH / f"music_{qunnum}.mp3", format="mp3")
    return TEMP_PATH / f"music_{qunnum}.mp3", TEMP_PATH / f"music_{qunnum}_end.mp3"


def cutSE(musicid: int, qunnum: int) -> Tuple[Path, Path]:
    """
    裁剪歌曲音效mp3
    """
    musicpath = SEdir / f'{musicid}.mp3'
    length = MP3(musicpath).info.length
    se = AudioSegment.from_mp3(musicpath)
    starttime = random.randint(2, int(length) - 30)
    cut = se[starttime * 1000: starttime * 1000 + 20000]
    cut.export(TEMP_PATH / f"music_{qunnum}.mp3", format="mp3", bitrate="96k")

    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        musics = json.load(f)
    for musicdata in musics:
        if musicdata['id'] == musicid:
            break
    vocal = defaultVocal(musicid)
    musicpath = data_path / f'ondemand/music/long/{vocal}/{vocal}.mp3'
    music = AudioSegment.from_mp3(musicpath).apply_gain(-3)
    cut2 = music[starttime * 1000 + musicdata['fillerSec'] * 1000: starttime * 1000 + 20000 + musicdata['fillerSec'] * 1000]
    mix = cut.overlay(cut2)
    mix.export(TEMP_PATH / f"music_{qunnum}_mix.mp3", format="mp3", bitrate="96k")
    return TEMP_PATH / f"music_{qunnum}.mp3", TEMP_PATH / f"music_{qunnum}_end.mp3"


async def endgame(group_id: int, self_id: int, game_type: str, user_qq: Optional[int] = None,  gameover: bool = False, advanceover: bool = False):
    global pjskguess
    try:
        print('判断游戏')
        # 判断游戏是否进行中
        if pjskguess[game_type][group_id].get('isgoing', False):
            print('游戏进行中')
            msgs = []
            file = pjskguess[game_type][group_id]['file']
            endfile = pjskguess[game_type][group_id]['endfile']
            # 收到正确回答，提前结束游戏
            if gameover:
                print('回答正确')
                qq = pjskguess[game_type][group_id]['userid']
                if pjskguess[game_type][group_id]['tips'] is None:
                    tipcount = 0
                else:
                    tipcount = max_tips_count - len(pjskguess[game_type][group_id]['tips'])
                diff = pjskguess[game_type][group_id]['diff']
                # 针对猜曲
                if game_type == GUESS_MUSIC:
                    musicname = pjskguess[game_type][group_id]['musicname']
                    # 结算金币 按难度决定基础奖励
                    rdgold = random.randint(0, {1: 15, 2: 30, 3: 45, 4: 30, 5: 45, 6: 45}.get(diff))
                    gold = {1: 50, 2: 200, 3: 500, 4: 200, 5: 500, 6: 350}.get(diff) + rdgold
                    # 游戏中使用了提示功能，奖励每次扣除25%
                    gold = math.ceil(gold - tipcount * gold // 4)
                    # 游戏发起者以外的人回答正确，0.9倍率
                    if user_qq and user_qq != pjskguess[game_type][group_id]['userid']:
                        gold = math.ceil(0.9 * gold)
                    if diff in [1, 2, 3, 6]:
                        msgs.append(at(qq)+f"您猜对了，奖励{gold}金币！(测试阶段，这是假的)\n正确答案：{musicname}")
                        msgs.append(MessageSegment.image(f'file:///{endfile.absolute()}'))
                    else:
                        msgs.append(at(qq) + f"您猜对了，奖励{gold}金币！(测试阶段，这是假的)\n正确答案：{musicname}")
                        msgs.append(MessageSegment.record(f'file:///{endfile.absolute()}'))
                # 针对猜卡面
                else:
                    cardname = pjskguess[game_type][group_id]['cardname']
                    charaname = pjskguess[game_type][group_id]['charaname']
                    # 结算金币 按难度决定基础奖励
                    rdgold = random.randint(0, {1: 15, 2: 30, 3: 25}.get(diff))
                    gold = {1: 50, 2: 200, 3: 500}.get(diff) + rdgold
                    # 游戏中使用了提示功能，奖励每次扣除25%
                    gold = math.ceil(gold - tipcount * gold // 4)
                    # 游戏发起者以外的人回答正确，0.9倍率
                    if user_qq and user_qq != pjskguess[game_type][group_id]['userid']:
                        gold = math.ceil(0.9 * gold)
                    msgs.append(at(qq) + f"您猜对了，奖励{gold}金币！(测试阶段，这是假的)\n正确答案：{cardname} - {charaname}" + MessageSegment.image(f'file:///{endfile.absolute()}'))
                # 记录进数据库
                print('记录进数据库')
                user_qq = user_qq if user_qq is not None else pjskguess[game_type][group_id]['userid']
                await PjskGuessRank.add_count(user_qq, group_id, game_type, int(diff))
                # await BagUser.add_gold(user_qq, group_id, gold)
            # 时间到自然结束游戏 或 提前结束
            else:
                print('时间到')
                _over = '提前结束' if advanceover else '时间到'
                # 针对猜曲
                if game_type == GUESS_MUSIC:
                    musicname = pjskguess[game_type][group_id]['musicname']
                    if pjskguess[game_type][group_id]['diff'] in [1, 2, 3, 6]:
                        msgs.append(
                            f"{_over}，正确答案：{musicname}" +
                            MessageSegment.image(f'file:///{endfile.absolute()}')
                        )
                    else:
                        msgs.append(f"{_over}，正确答案：{musicname}")
                        msgs.append(MessageSegment.record(f'file:///{endfile.absolute()}'))
                # 针对猜卡面
                elif game_type == GUESS_CARD:
                    cardname = pjskguess[game_type][group_id]['cardname']
                    msgs.append(
                        f"{_over}，正确答案：{cardname}" +
                        MessageSegment.image(f'file:///{endfile.absolute()}')
                    )
            print(pjskguess)
            pjskguess[game_type][group_id].clear()
            # 发送信息
            print('发送消息')
            print(msgs)
            bot: Bot = get_bot(str(self_id))
            try:
                for msg in msgs:
                    await bot.send_msg(message_type='group', group_id=group_id, message=msg)
            except:
                pass
            print('删除文件')
            if file and file.exists():
                file.unlink()
            if endfile and endfile.exists():
                endfile.unlink()
    except Exception as e:
        raise e
        pass