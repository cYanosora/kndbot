import random
from typing import Tuple
from nonebot import on_regex
from nonebot.log import logger
from nonebot.params import RegexGroup
from nonebot.adapters.onebot.v11 import MessageSegment, GROUP, GroupMessageEvent
from configs.config import NICKNAME
from manager import Config
from utils.limit_utils import ignore_mute
from .render_pic import render
from .weather_data import Weather, ConfigError, CityNotFoundError, APIError

__plugin_name__ = "天气查询"
__plugin_type__ = "实用工具"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    天气查询，数据来自和风天气
    指令：
        [城市]天气
        天气[城市]
""".strip()
__plugin_settings__ = {
    "cmd": ["查询天气", "天气", "天气查询", "查天气"],
}
__plugin_cd_limit__ = {"cd": 5, "rst": "别急，[cd]s后再用！[at]",}
__plugin_count_limit__ = {
    "max_count": 15,
    "limit_type": "user",
    "rst": "咱累了，建议还是看天气预报呢[at]",
}

__plugin_configs__ = {
    "APIKEY": {
        "value": "",
        "help": "和风天气api的key，需要从官网注册账号自行获取",
        "default_value": ""
    },
    "APITYPE": {
        "value": 0,
        "help": "和风天气api的类型",
        "default_value": 0
    },
}

weather = on_regex(
    r".{0,10}?(.*)(?:的|查询)?天气(?:查询)?(.*)?.{0,10}$",
    priority=5,
    permission=GROUP,
    block=True
)


@weather.handle()
async def _(event: GroupMessageEvent, args: Tuple[str, ...] = RegexGroup()):
    if args[0].strip() and args[1].strip():
        ignore_mute(f"{event.group_id}_{event.user_id}")
        return
    city = args[0].strip() or args[1].strip()
    if not city:
        ignore_mute(f"{event.group_id}_{event.user_id}")
        await weather.finish(f"没告诉咱是哪个地方的话，怎么查嘛...")
    if "sekai" in city:
        await weather.finish(random.choice([
            "sekai的天气？嘛...倒是没怎么注意过呢\n(话说sekai里有天气的概念吗",
            "sekai的天气吗...因为光线很暗所以应该算是阴天吧...",
        ]))
    api_key = Config.get_config("weather", "APIKEY", None)
    api_type = Config.get_config("weather", "APITYPE", None)
    w_data = Weather(city_name=city, api_key=api_key, api_type=api_type)
    try:
        await w_data.load_data()
    except CityNotFoundError:
        ignore_mute(f"{event.group_id}_{event.user_id}")
        await weather.finish(f"{NICKNAME}没查到！试试查sekai的天气？")
    except APIError:
        ignore_mute(f"{event.group_id}_{event.user_id}")
        await weather.finish(f"欸嘿，突然就不想查了，自己去看天气预报吧")
    img = await render(w_data)
    logger.info(
        f"USER {event.user_id} GROUP {event.group_id} 查询了 {city} 天气"
    )
    await weather.finish(MessageSegment.image(img))


