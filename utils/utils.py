from datetime import datetime
from collections import defaultdict
from nonebot import require
from configs.config import SYSTEM_PROXY
from typing import List, Union, Optional, Type, Any
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.matcher import matchers, Matcher
from functools import wraps
import httpx
import nonebot
import pytz
import pypinyin
import time
from configs.path_config import TEMP_PATH
try:
    import ujson as json
except ModuleNotFoundError:
    import json


scheduler = require("nonebot_plugin_apscheduler").scheduler
htmlrender = require("nonebot_plugin_htmlrender")
avatar_path = TEMP_PATH / 'avatars'
if not avatar_path.exists():
    avatar_path.mkdir(parents=True, exist_ok=True)

# 全局字典
GDict = {
    "run_sql": [],                  # 需要启动前运行的sql语句
    "_shop_before_handle": {},      # 商品使用前函数
    "_shop_after_handle": {},      # 商品使用后函数
}


class CountLimiter:
    """
    次数检测工具，检测调用次数是否超过设定值
    """

    def __init__(self, max_count: int):
        self.max_count = max_count
        self.count = defaultdict(int)

    def isexist(self, key: Any) -> bool:
        if key in self.count.keys():
            return True
        return False

    def add(self, key: Any, num: int = 1):
        self.count[key] += num

    def sub(self, key: Any, num: int = 1):
        if self.count[key]:
            self.count[key] -= num

    def get_count(self, key: Any) -> int:
        return self.count[key]

    def check(self, key: Any) -> bool:
        if self.count[key] >= self.max_count:
            self.count.pop(key)
            return True
        else:
            return False

    def clear(self, key: Any):
        if key in self.count:
            self.count.pop(key)


class UserBlockLimiter:
    """
    检测用户是否正在调用命令
    """

    def __init__(self, limit_block_time: int = 30):
        self._hook_time = time.time()
        self.limit_time = limit_block_time
        self.flag_data = defaultdict(bool)
        self.time = time.time()

    @staticmethod
    def __pre_hook(f):
        """解除所有超时阻塞"""
        @wraps(f)
        def decorated(*args, **kwargs):
            cls = args[0].__class__
            cls.clean_data(args[0])
            return f(*args, **kwargs)
        return decorated

    def clean_data(self):
        if time.time() - self._hook_time > 6 * 3600:
            self._hook_time = time.time()
            for key in self.flag_data.copy():
                if time.time() - self.time > self.limit_time or self.flag_data[key] is False:
                    self.flag_data.pop(key)

    # 阻塞
    def set_true(self, key: Any):
        self.time = time.time()
        self.flag_data[key] = True

    # 解除阻塞
    def set_false(self, key: Any):
        self.flag_data[key] = False

    # 检查阻塞并尝试解除阻塞
    @__pre_hook
    def check(self, key: Any) -> bool:
        if time.time() - self.time > self.limit_time:
            self.set_false(key)
        return self.flag_data[key]


class FreqLimiter:
    """
    命令冷却，检测用户是否处于冷却状态
    """

    def __init__(self, default_cd_seconds: int, default_count_limit: int = 1):
        """
        :param default_cd_seconds: 冷却时间范围
        :param default_count_limit: 冷却时间内最多限制次数
        """
        self._hook_time = time.time()
        self.default_cd = default_cd_seconds
        self.next_time = defaultdict(float)
        self.count = CountLimiter(default_count_limit)

    @staticmethod
    def __pre_hook(f):
        """解除所有超时阻塞"""
        @wraps(f)
        def decorated(*args, **kwargs):
            cls = args[0].__class__
            cls.clean_data(args[0])
            return f(*args, **kwargs)
        return decorated

    def clean_data(self):
        if time.time() - self._hook_time > 6 * 3600:
            self._hook_time = time.time()
            for key in self.next_time.copy():
                if time.time() >= self.next_time[key]:
                    self.next_time.pop(key)
                    self.count.clear(key)

    @__pre_hook
    def check(self, key: Any) -> bool:
        return time.time() >= self.next_time[key]

    def remove_cd(self, key: Any):
        if key in self.next_time:
            self.next_time.pop(key)
            self.count.clear(key)

    def get_cd_count(self, key):
        return self.count.get_count(key)

    def sub_cd_count(self, key):
        self.count.sub(key)

    @__pre_hook
    def count_check(self, key: Any) -> bool:
        # 若cd冷却时段进入新cd区间 或 cd冷却时段内使用次数未耗尽
        if self.check(key) or self.count.get_count(key) < self.count.max_count:
            return True
        else:
            return False

    def start_cd(self, key: Any, cd_time: int = 0, cd_count: int = 1):
        # 若cd冷却时段进入新cd区间,重新计数
        if self.check(key):
            self.next_time[key] = time.time() + (
                cd_time if cd_time > 0 else self.default_cd
            )
            self.count.clear(key)
            self.count.add(key, cd_count)
        else:
            self.count.add(key, cd_count)

    def left_time(self, key: Any) -> float:
        return self.next_time[key] - time.time()


class DailyNumberLimiter:
    """
    每日调用命令次数限制
    """

    tz = pytz.timezone("Asia/Shanghai")

    def __init__(self, max_num):
        self.today = -1
        self.count = defaultdict(int)
        self.max = max_num

    def check(self, key) -> bool:
        day = datetime.now(self.tz).day
        if day != self.today:
            self.today = day
            self.count.clear()
        return bool(self.count[key] < self.max)

    def get_num(self, key):
        return self.count[key]

    def increase(self, key, num=1):
        self.count[key] += num

    def decrease(self, key, num=1):
        num = self.count[key] if num > self.count[key] else num
        self.count[key] -= num

    def reset(self, key):
        self.count[key] = 0


def timeremain(t: float):
    """
    说明：
        将时间戳转换为中文时间字符串
    参数：
        :param t: 时间戳
    """
    if t < 60:
        return f'{int(t)}秒'
    elif t < 3600:
        result = f'{int(t / 60)}分'
        if int(t % 60):
            result += f'{int(t % 60)}秒'
    elif t < 3600 * 24:
        hours = int(t / 3600)
        remain = t - 3600 * hours
        result = f'{int(t / 3600)}小时'
        if int(remain / 60):
            result += f'{int(remain / 60)}分'
        if int(remain % 60):
            result += f'{int(remain % 60)}秒'
    else:
        days = int(t / 3600 / 24)
        remain = t - 3600 * 24 * days
        result = f'{int(days)}天{timeremain(remain)}'
    return result


def is_number(s: str) -> bool:
    """
    说明：
        检测 s 是否为数字
    参数：
        :param s: 文本
    """
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata

        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False


def get_bot() -> Optional[Bot]:
    """
    说明：
        获取 bot 对象
    """
    try:
        return list(nonebot.get_bots().values())[0]
    except IndexError:
        return None


def get_matchers() -> List[Type[Matcher]]:
    """
    获取所有响应器
    """
    _matchers = []
    for i in matchers.keys():
        for matcher in matchers[i]:
            _matchers.append(matcher)
    return _matchers


def get_message_at(data: Union[str, Message]) -> List[int]:
    """
    说明：
        获取消息中所有的 at 对象的 qq
    参数：
        :param data: event.raw_message
    """
    qq_list = []
    if isinstance(data, str):
        data = Message(data)
    for msg_seg in data:
        if msg_seg.type == 'at' and msg_seg.data.get("qq", "all") != "all":
            qq_list.append(int(msg_seg.data['qq']))
    return qq_list


def get_message_img(data: Union[str, Message]) -> List[str]:
    """
    说明：
        获取消息中所有的 图片 的链接
    参数：
        :param data: event.json()
    """
    img_list = []
    if isinstance(data, str):
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "image":
                img_list.append(msg["data"]["url"])
    else:
        for seg in data["image"]:
            img_list.append(seg.data["url"])
    return img_list


def get_message_text(data: Union[str, Message]) -> str:
    """
    说明：
        获取消息中 纯文本 的信息
    参数：
        :param data: event.json()
    """
    result = ""
    if isinstance(data, str):
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "text":
                result += msg["data"]["text"].strip() + " "
        return result.strip()
    else:
        for seg in data["text"]:
            result += seg.data["text"] + " "
    return result


def get_message_record(data: Union[str, Message]) -> List[str]:
    """
    说明：
        获取消息中所有 语音 的链接
    参数：
        :param data: event.json()
    """
    record_list = []
    if isinstance(data, str):
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "record":
                record_list.append(msg["data"]["url"])
    else:
        for seg in data["record"]:
            record_list.append(seg.data["url"])
    return record_list


def get_message_json(data: str) -> List[dict]:
    """
    说明：
        获取消息中所有 json
    参数：
        :param data: event.json()
    """
    try:
        json_list = []
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "json":
                json_list.append(msg["data"])
        return json_list
    except KeyError:
        return []


def get_local_proxy():
    """
    说明：
        获取 config.py 中设置的代理
    """
    return SYSTEM_PROXY if SYSTEM_PROXY else None


def is_chinese(word: str) -> bool:
    """
    说明：
        判断字符串是否为纯中文
    参数：
        :param word: 文本
    """
    for ch in word:
        if not "\u4e00" <= ch <= "\u9fff":
            return False
    return True


async def get_user_avatar(qq: int) -> Optional[bytes]:
    """
    说明：
        快捷获取用户头像
    参数：
        :param qq: qq号
    """
    file = avatar_path / f'u{qq}.jpg'
    if file.exists():
        if file.stat().st_ctime + 86400 > time.time():
            with open(file, 'br') as f:
                return f.read()
        else:
            file.unlink()
    url = f"http://q1.qlogo.cn/g?b=qq&nk={qq}&s=160"
    async with httpx.AsyncClient() as client:
        for _ in range(3):
            try:
                content = (await client.get(url)).content
                with open(file, 'bw') as f:
                    f.write(content)
                return content
            except TimeoutError:
                pass
    return None


async def get_group_avatar(group_id: int) -> Optional[bytes]:
    """
    说明：
        快捷获取用群头像
    参数：
        :param group_id: 群号
    """
    file = avatar_path / f'g{group_id}.jpg'
    if file.exists():
        if file.stat().st_ctime + 86400 > time.time():
            with open(file, 'br') as f:
                return f.read()
        else:
            file.unlink()
    url = f"http://p.qlogo.cn/gh/{group_id}/{group_id}/640/"
    async with httpx.AsyncClient() as client:
        for _ in range(3):
            try:
                content = (await client.get(url)).content
                with open(file, 'bw') as f:
                    f.write(content)
                return content
            except TimeoutError:
                pass
    return None


def cn2py(word: str) -> str:
    """
    说明：
        将字符串转化为拼音
    参数：
        :param word: 文本
    """
    temp = ""
    for i in pypinyin.pinyin(word, style=pypinyin.NORMAL):
        temp += "".join(i)
    return temp


def change_pixiv_image_links(
    url: str, size: Optional[str] = None, nginx_url: Optional[str] = None
):
    """
    说明：
        根据配置改变图片大小和反代链接
    参数：
        :param url: 图片原图链接
        :param size: 模式
        :param nginx_url: 反代
    """
    if size == "master":
        img_sp = url.rsplit(".", maxsplit=1)
        url = img_sp[0]
        img_type = img_sp[1]
        url = url.replace("original", "master") + f"_master1200.{img_type}"
    if nginx_url:
        url = (
            url.replace("i.pximg.net", nginx_url)
            .replace("i.pixiv.cat", nginx_url)
            .replace("_webp", "")
        )
    return url


def get_message_img_file(data: Union[str, Message]) -> List[str]:
    """
    说明：
        获取消息中所有的 图片file
    参数：
        :param data: event.json()
    """
    file_list = []
    if isinstance(data, str):
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "image":
                file_list.append(msg["data"]["file"])
    else:
        for seg in data["image"]:
            file_list.append(seg.data["file"])
    return file_list