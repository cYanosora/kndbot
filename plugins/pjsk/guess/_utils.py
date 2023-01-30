from typing import Tuple, Optional
from nonebot import require
from utils.http_utils import AsyncHttpx
from ._config import GUESS_CARD, GUESS_MUSIC, pjskguess
from .._config import data_path
from .._song_utils import get_songs_data, save_songs_data
require('image_management')
from plugins.image_management.pjsk_images.pjsk_db_source import PjskAlias
try:
    import ujson as json
except:
    import json


def pre_check(gid: int):
    global pjskguess
    try:
        if pjskguess[GUESS_CARD][gid].get('isgoing', False):
            return '猜卡面已经开始，请等待这轮结束！(开启者发送 结束猜卡面 可以提前结束)'
    except KeyError:
        pass
    try:
        if pjskguess[GUESS_MUSIC][gid].get('isgoing', False):
            return '猜曲已经开始，请等待这轮结束！(开启者发送 结束猜曲 可以提前结束)'
    except KeyError:
        pass
    return ''


async def aliasToMusicId(alias: str) -> Tuple[int, str]:
    # 首先查询本地数据库有无对应别称id
    data = await get_songs_data(alias, isfuzzy=False)
    # 若无结果则访问uniapi
    if data['status'] != 'success':
        url = rf'https://api.unipjsk.com/getsongid/{alias}'
        data = (await AsyncHttpx.get(url)).json()
        # 无结果则尝试在本地模糊搜索得到结果
        if data['status'] != 'success':
            data = await get_songs_data(alias, isfuzzy=True)
            # 若还无结果则说明没有歌曲信息
            if data['status'] != 'success':
                return 0, ''
        # 有结果则尝试更新api返回的别称信息存入本地数据库
        else:
            await save_songs_data(data['musicId'])
    name = data.get('translate', '') or data.get('title', '这个')
    return data['musicId'], name


async def aliasToCharaId(alias: str, group_id: Optional[int] = None) -> Tuple[int, str]:
    chard2id = {
        'ick': 1, 'saki': 2, 'hnm': 3, 'shiho': 4,
        'mnr': 5, 'hrk': 6, 'airi': 7, 'szk': 8,
        'khn': 9, 'an': 10, 'akt': 11, 'toya': 12,
        'tks': 13, 'emu': 14, 'nene': 15, 'rui': 16,
        'knd': 17, 'mfy': 18, 'ena': 19, 'mzk': 20,
        'miku': 21, 'rin': 22, 'len': 23, 'luka': 24, 'meiko': 25, 'kaito': 26
    }
    id2name = {
        17: '宵崎奏',18: '朝比奈真冬',19: '东云绘名',20: '晓山瑞希',
        9: '小豆泽心羽',10: '白石杏',11: '东云彰人',12: '青柳冬弥',
        5: '花里实乃理',6: '桐谷遥',7: '桃井爱莉',8: '日野森雫',
        1: '星乃一歌',2: '天马咲希',3: '望月穗波',4: '日野森志步',
        13: '天马司',14: '凤绘梦',15: '草薙宁宁',16: '神代类',
        21: '初音未来',22: '镜音铃',23: '镜音连',24: '巡音流歌',25: 'MEIKO',26: 'KAITO'
    }
    _id = chard2id.get(alias, 0)
    if _id == 0:
        if group_id is None:
            name = await PjskAlias.query_name(alias)
        else:
            name = await PjskAlias.query_name(alias, group_id=group_id)
        charaid = chard2id.get(name, 0)
    else:
        charaid = _id
    charaname = id2name.get(charaid, '')
    return charaid, charaname


# 其他
def defaultVocal(musicid: int) -> str:
    """
    默认vocal
    :returns: 歌曲asset名称
    """
    with open(data_path / 'musicVocals.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    assetbundleName = ''
    for vocal in data:
        if vocal['musicId'] == musicid:
            if vocal['musicVocalType'] == 'sekai' or vocal['musicVocalType'] == 'instrumental':
                return vocal['assetbundleName']
            elif vocal['musicVocalType'] == 'original_song' or vocal['musicVocalType'] == 'virtual_singer':
                assetbundleName = vocal['assetbundleName']
    return assetbundleName
