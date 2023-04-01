import asyncio
import datetime
import hashlib
import time
import requests
import yaml
from pathlib import Path
from typing import Union
from PIL import Image
from zhconv import convert
from services import logger
from utils.http_utils import AsyncHttpx
from utils.user_agent import get_user_agent
from utils.utils import scheduler
from ._config import json_url, json_url_bak, db_url, data_path, db_url_bak, lab_headers


class PjskDataUpdate:
    def __init__(self, path: Union[str, Path]):
        if isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path
        if not self.path.exists():
            self.path.mkdir(parents=True, exist_ok=True)

    async def update_music_data(self, raw: str, block: bool = False):
        try:
            urls = [
                f'https://raw.fastgit.org/watagashi-uni/Unibot/main/masterdata/realtime/{raw}',
                f"https://raw.githubusercontent.com/watagashi-uni/Unibot/main/masterdata/realtime/{raw}"
            ]
            for i,url in enumerate(urls):
                if block:
                    resp = requests.get(url, headers=lab_headers)
                else:
                    resp = await AsyncHttpx.get(url, headers=lab_headers)
                if resp.status_code == 200:
                    break
                elif i != len(urls) - 1:
                    continue
                else:
                    logger.warning(f"{raw}下载失败，网络不太好，尝试使用备用网址下载")
                    return
            jsondata = resp.content
            logger.info(f'{raw}下载成功')
            filepath = self.path / 'realtime'
            if not filepath.exists():
                filepath.mkdir(parents=True, exist_ok=True)
            filepath = filepath / raw
            if not filepath.exists():
                with open(filepath, 'wb') as f:
                    f.write(jsondata)
                    logger.info(f'初次创建{raw}')
            else:
                with open(filepath, 'rb') as f:
                    if jsondata and hashlib.md5(f.read()).hexdigest() != hashlib.md5(jsondata).hexdigest():
                        with open(filepath, "wb") as f:
                            f.write(jsondata)
                            logger.info(f'更新{raw}')
                    else:
                        logger.info(f'无需更新{raw}')
        except Exception as e:
            logger.info(f'{raw}下载失败, 错误原因:{e}')

    async def update_music_meta_data(self, raw: str, block: bool = False):
        try:
            url = f'https://storage.sekai.best/sekai-best-assets/{raw}'
            if block:
                jsondata = requests.get(url, headers=lab_headers).content
            else:
                jsondata = (await AsyncHttpx.get(url, headers=lab_headers)).content
            logger.info(f'{raw}下载成功')
            filepath = self.path / 'realtime'
            if not filepath.exists():
                filepath.mkdir(parents=True, exist_ok=True)
            filepath = filepath / raw
            if not filepath.exists():
                with open(filepath, 'wb') as f:
                    f.write(jsondata)
                    logger.info(f'初次创建{raw}')
            else:
                with open(filepath, 'rb') as f:
                    if jsondata and hashlib.md5(f.read()).hexdigest() != hashlib.md5(jsondata).hexdigest():
                        with open(filepath, "wb") as f:
                            f.write(jsondata)
                            logger.info(f'更新{raw}')
                    else:
                        logger.info(f'无需更新{raw}')
        except Exception as e:
            logger.info(f'{raw}下载失败, 错误原因:{e}')

    async def update_translate_data(self, raw: str, block: bool = False):
        filepath = self.path / 'translate.yaml'
        if not filepath.exists():
            filepath.touch()
            translation = {}
            logger.info(f'首次创建{raw}')
        else:
            with open(filepath, encoding='utf-8') as f:
                translation = yaml.load(f, Loader=yaml.FullLoader)
                translation = translation if translation else {}
        if not translation.get(raw):
            translation[raw] = {}
        try:
            url = f'https://raw.fastgit.org/Sekai-World/sekai-i18n/main/zh-TW/{raw}.json'
            if block:
                data = requests.get(url).json()
            else:
                data = (await AsyncHttpx.get(url)).json()
            logger.info(f'{raw}翻译下载成功')
        except Exception as e:
            logger.warning(f'{raw}翻译下载失败，错误原因:{e}')
            return
        for i in data:
            try:
                translation[raw][int(i)]
            except KeyError:
                zhhan = convert(data[i], 'zh-cn')
                translation[raw][int(i)] = zhhan
                logger.info(f'更新翻译{raw} {i} {zhhan}')
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(translation, f, allow_unicode=True)

    async def update_jp_game_data(self, raw: str, block: bool = False):
        for url in [json_url, json_url_bak]:
            try:
                url += f'/{raw}'
                if block:
                    jsondata = requests.get(url, headers=lab_headers).content
                else:
                    jsondata = (await AsyncHttpx.get(url, headers=lab_headers)).content
                logger.info(f'{raw}下载成功')
                filepath = self.path / f'{raw}'
                if not filepath.exists():
                    filepath.touch()
                with open(filepath, 'rb') as f:
                    if jsondata and hashlib.md5(f.read()).hexdigest() != hashlib.md5(jsondata).hexdigest():
                        with open(filepath, "wb") as f:
                            f.write(jsondata)
                            logger.info(f'更新{raw}')
                    else:
                        logger.info(f'无需更新{raw}')
                break
            except Exception as e:
                logger.warning(f'{raw}下载失败, 错误原因:{e}')
                continue

    async def update_jp_assets(self, path: str, raw: str, block: bool = False):
        path = path.replace('\\', '/')
        raw = raw.replace('\\', '/')
        url = db_url_bak + rf'/{path}/{raw}'
        filepath = self.path / path
        if not filepath.exists():
            filepath.mkdir(parents=True, exist_ok=True)
        filepath = filepath / raw
        if not filepath.exists():
            if await self._download_file(url, path=filepath, block=block):
                logger.info(f'{path}/{raw}下载成功')
            else:
                url = db_url + rf'/{path}/{raw}'
                if await self._download_file(url, path=filepath, block=block):
                    logger.info(f'{path}/{raw}下载成功')

    async def _download_file(self, url: str, path: Path, headers=None, block: bool = False):
        try:
            if headers is None:
                headers = get_user_agent()
            if block:
                resp = requests.get(url, headers=headers)
            else:
                resp = await AsyncHttpx.get(url, headers=headers)
            if resp.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(resp.content)
                return True
            else:
                logger.warning(f'{url}资源路径不存在！')
        except Exception as e:
            logger.warning(f'错误信息：{e}')
        return False

    async def get_asset(self, path: str, raw: str, block: bool = False, download: bool = True) -> Image:
        if not (self.path / path / raw).exists() and download:
            logger.warning(f'缺失资源{path}/{raw}，尝试下载此资源中...')
            await self.update_jp_assets(path, raw, block=block)
        try:
            if raw.endswith('.png') or raw.endswith('.jpg') or raw.endswith('.jpeg'):
                pic = Image.open(self.path / path / raw)
                return pic
        except FileNotFoundError:
            logger.warning(f'找不到资源{path}/{raw}')
            return None
        except Exception as e:
            logger.warning(f'资源调用失败，错误信息：{e}')
            return None

pjsk_update_manager = PjskDataUpdate(data_path)


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=12,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=3)
)
async def check_event_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（活动）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新sk、rk所需json文件
    await pjsk_update_manager.update_jp_game_data('events.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('rankMatchSeasons.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('cheerfulCarnivalTeams.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('bondsHonors.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time * 3}秒, 额外等待时间{wait_time * 3}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=12,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=4)
)
async def check_eventinfo_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（活动查询）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新活动查询所需json文件
    await pjsk_update_manager.update_jp_game_data('eventCards.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('eventDeckBonuses.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('gameCharacterUnits.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time * 2}秒, 额外等待时间{wait_time * 2}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=12,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=2)
)
async def check_cards_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（卡面查询）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新卡面查询所需json文件
    await pjsk_update_manager.update_jp_game_data('cardCostume3ds.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('costume3ds.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('gameCharacters.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('cards.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time * 3}秒, 额外等待时间{wait_time * 3}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=12,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=1)
)
async def check_profile_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（档案）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新pjskprofile所需json文件
    await pjsk_update_manager.update_jp_game_data('honors.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('honorGroups.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time}秒, 额外等待时间{wait_time}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=12,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=2)
)
async def check_pjskinfo_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（谱面）", block=block)
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新pjskinfo所需json文件
    await pjsk_update_manager.update_jp_game_data('musicVocals.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('outsideCharacters.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time}秒, 额外等待时间{wait_time}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=6,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=5)
)
async def check_songs_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（歌曲）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新音乐数据
    await pjsk_update_manager.update_music_meta_data('music_metas.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_music_data('musicDifficulties.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_music_data('musics.csv', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('musicDifficulties.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('musics.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time}秒, 额外等待时间{wait_time * 3}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=6,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=6)
)
async def check_trans_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（翻译）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新翻译数据
    await pjsk_update_manager.update_translate_data('music_titles', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_translate_data('event_name', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_translate_data('card_prefix', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_translate_data('cheerful_carnival_teams', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_translate_data('card_gacha_phrase', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_translate_data('card_skill_name', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_translate_data('skill_desc', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time * 3}秒, 额外等待时间{wait_time * 6}秒！")


# 分组自动更新烧烤数据
@scheduler.scheduled_job(
    'interval',
    hours=6,
    # minutes=5,
    start_date=datetime.datetime.now().date() + datetime.timedelta(hours=14, minutes=7)
)
async def check_event_resources(block: bool = False, iswait: bool = True):
    logger.info("开始自动更新pjsk游戏数据！（卡面信息）")
    st = time.time()
    if iswait:
        wait_time = 5
    else:
        wait_time = 0
    # 更新sk、rk所需json文件
    await pjsk_update_manager.update_jp_game_data('eventMusics.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('gachas.json', block=block)
    await asyncio.sleep(wait_time)
    await pjsk_update_manager.update_jp_game_data('skills.json', block=block)
    spread_time = time.time() - st
    logger.info(f"pjsk游戏数据更新完毕,耗时{spread_time - wait_time * 3}秒, 额外等待时间{wait_time * 2}秒！")
