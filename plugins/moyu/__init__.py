from nonebot import logger, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP, MessageSegment
from utils.http_utils import AsyncHttpx
from utils.message_builder import reply
try:
    import ujson as json
except ModuleNotFoundError:
    import json
__plugin_name__ = "摸鱼日历"
__plugin_type__ = "资讯类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    摸鱼一时爽, 一直摸鱼一直爽, 周日就别看了(
    指令：
        摸鱼日历
""".strip()
__plugin_settings__ = {
    "cmd": ["摸鱼日历"],
}
__plugin_cd_limit__ = {"cd": 300, "rst": "别急，[cd]s后再继续摸鱼！[at]",}
__plugin_block_limit__ = {"rst": "别急，摸鱼日历正在生成中！"}
__plugin_count_limit__ = {
    "max_count": 1,
    "limit_type": "user",
    "rst": "你今天已经看过摸鱼日历了，不许再摸鱼了[at]",
}

moyu_matcher = on_command("摸鱼日历", permission=GROUP, priority=5, block=True)


@moyu_matcher.handle()
async def moyu(event: GroupMessageEvent):
    await moyu_matcher.send("想摸鱼了吗？我去找找今天的摸鱼日历，等等哦")
    moyu_img = await get_calendar()
    if moyu_img:
        await moyu_matcher.finish(reply(event.message_id) + MessageSegment.image(moyu_img))
        logger.info(f"USER {event.user_id}  GROUP {event.group_id} 使用了摸鱼日历功能")
    else:
        await moyu_matcher.finish(reply(event.message_id) + "日历获取失败，要不然你还是别摸鱼了吧(・∀・*)")
        logger.warning(f"USER {event.user_id}  GROUP {event.group_id} 摸鱼日历功能使用失败!")


async def get_calendar() -> str:
    try:
        response = await AsyncHttpx.get(f"https://api.j4u.ink/v1/store/other/proxy/remote/moyu.json")
        content = json.loads(response.text)
        return content["data"]["moyu_url"]
    except:
        logger.warning(f"摸鱼日历获取失败，错误码：{response.status_code}")
        return ""
