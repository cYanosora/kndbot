from services import logger
from nonebot.adapters.onebot.v11 import Message, ActionFailed, GroupMessageEvent, GROUP
import ujson as json
from nonebot import on_command
from utils.http_utils import AsyncHttpx
from utils.message_builder import reply

__plugin_name__ = "60s读世界"
__plugin_type__ = "资讯类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    看看每天世界都发生了什么事情
    指令：
        60s读世界/读世界/60s看世界/看世界
""".strip()
__plugin_settings__ = {
    "cmd": ["看世界", "60s看世界", "读世界", "60s读世界"],
}
__plugin_cd_limit__ = {"cd": 60, "rst": "不久前才发了今日份新闻诶，看看上面的消息吧，不然还请等[cd]秒后再用呢~", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "正在总结今天发生的事情..."}
__plugin_count_limit__ = {
    "max_count": 3,
    "limit_type": "user",
    "rst": "你今天已经查询过多次了哦，还请明天再继续呢[at]",
}

read_world = on_command(
    "60s看世界",
    aliases={"60s读世界", "读世界", "看世界"},
    permission=GROUP,
    priority=5,
    block=True
)

@read_world.handle()
async def _(event: GroupMessageEvent):
    await read_world.send("正在总结今天发生的事情，请稍作等待(－ω－)")
    try:
        result = await suijitu()
    except:
        result = Message("呜呜，出错了，无法为你总结今天的事情惹(;ω;)")
    try:
        await read_world.finish(message=reply(event.message_id) + Message(result))
        logger.info(f"USER {event.user_id}  GROUP {event.group_id} 使用了60s读世界功能")
    except ActionFailed:
        await read_world.finish(reply(event.message_id) + "图片发送失败，可能是遭到风控。")
        logger.warning(f"USER {event.user_id}  GROUP {event.group_id} 60s读世界功能使用失败!")


def remove_upprintable_chars(s):
    return ''.join(x for x in s if x.isprintable())  # 去除imageUrl可能存在的不可见字符


async def suijitu():
    url_list = ["https://api.iyk0.com/60s", "https://api.2xb.cn/zaob"]
    for url in url_list:
        try:
            retdata = (await AsyncHttpx.get(url)).text
            lst = json.loads(remove_upprintable_chars(retdata))['imageUrl']
        except:
            logger.info("60s读世界网页访问失败！")
            continue
        else:
            return Message(f"[CQ:image,file={lst}]")
