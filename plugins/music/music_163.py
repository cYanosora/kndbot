import json
import httpx
from dataclasses import dataclass
from typing import Union, Tuple, Protocol
from nonebot.adapters.onebot.v11 import MessageSegment
from utils.http_utils import AsyncHttpx
import difflib
from functools import reduce


async def search_qq(keyword: str) -> Union[str, MessageSegment]:
    url = "https://c.y.qq.com/splcloud/fcgi-bin/smartbox_new.fcg"
    params = {
        "format": "json",
        "inCharset": "utf-8",
        "outCharset": "utf-8",
        "notice": 0,
        "platform": "yqq.json",
        "needNewCode": 0,
        "uin": 0,
        "hostUin": 0,
        "is_xml": 0,
        "key": keyword,
    }
    resp = await AsyncHttpx.get(url, params=params)
    result = resp.json()
    if songs := result["data"]["song"]["itemlist"]:
        return MessageSegment.music("qq", songs[0]["id"])
    return "QQ音乐中找不到相关的歌曲"


async def search_163(keyword: str) -> Union[str, MessageSegment]:
    def func(x, y):
        return difflib.SequenceMatcher(None, x, y).ratio()
    try:
        # 搜索歌曲信息
        url = "https://music.163.com/api/cloudsearch/pc"
        params = {"s": keyword, "type": 1, "offset": 0, "limit": 3}
        resp = await AsyncHttpx.post(url, data=params)
        if resp.status_code != 200:
            return ""
        result = resp.json()
        # 获取歌曲id
        try:
            songs = result["result"]["songs"]
            songs_dict = {i["name"]: i["id"] for i in songs}
            song_name_list = songs_dict.keys()

            res = reduce(lambda x, y: x if func(x, keyword) > func(y, keyword) else y, song_name_list)
            song_id = songs_dict.get(res)
            if not song_id:
                return "网易云音乐中找不到相关的歌曲"
            return MessageSegment.music("163", song_id)
        except KeyError:
            return "出错了，请稍后再试"
    except:
        url = "http://music.163.com/api/search/get/"
        params = {"s": keyword, "limit": 1, "type": 1, "offset": 0}
        r = await AsyncHttpx.post(url,data=params)
        if r.status_code != 200:

            return ""
        result = json.loads(r.text)
        try:

            songs = result["result"]["songs"]
            songs_dict = {i["name"]: i["id"] for i in songs}
            song_name_list = songs_dict.keys()

            res = reduce(lambda x, y: x if func(x, keyword) > func(y, keyword) else y, song_name_list)
            song_id = songs_dict.get(res)
            if not song_id:

                return "网易云音乐中找不到相关的歌曲"
            return MessageSegment.music("163", song_id)
        except KeyError:

            return "出错了，请稍后再试"


async def search_bili(keyword: str) -> Union[str, MessageSegment]:
    search_url = "https://api.bilibili.com/audio/music-service-c/s"
    params = {"page": 1, "pagesize": 1, "search_type": "music", "keyword": keyword}
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url, params=params)
        result = resp.json()
    if songs := result["data"]["result"]:
        info = songs[0]
        return MessageSegment.music_custom(
            url=f"https://www.bilibili.com/audio/au{info['id']}",
            audio=info["play_url_list"][0]["url"],
            title=info["title"],
            content=info["author"],
            img_url=info["cover"],
        )
    return "B站音频区中找不到相关的歌曲"


class Func(Protocol):
    async def __call__(self, keyword: str) -> Union[str, MessageSegment]:
        ...


@dataclass
class Source:
    keywords: Tuple[str, ...]
    func: Func


sources = [
    Source(("163", "网易", "网易云"), search_163),
    Source(("qq", "QQ"), search_qq),
    # Source(("kugou", "酷狗"), search_kugou),
    # Source(("migu", "咪咕"), search_migu),
    Source(("bili", "bilibili", "b站", "B站"), search_bili),
]

