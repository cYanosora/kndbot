from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, GROUP
from nonebot.params import CommandArg
from services.log import logger
from ._data_source import gen_wbtop_pic, get_wbtop
from utils.utils import is_number
from configs.path_config import IMAGE_PATH
from utils.http_utils import AsyncPlaywright
import asyncio
import datetime
from utils.message_builder import reply

__plugin_name__ = "微博热搜"
__plugin_type__ = "资讯类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    在QQ上吃个瓜
    指令：
        微博热搜：发送实时热搜
        微博热搜 [id]：截图该热搜页面
    示例：
        微博热搜 5
""".strip()
__plugin_settings__ = {
    "cmd": ["微博热搜"],
}
__plugin_cd_limit__ = {"cd": 30, "rst": "别急，[cd]s后再用！[at]",}
__plugin_block_limit__ = {}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "你今天吃了多少次瓜了，别吃了![at]",
}

wbtop = on_command("微博热搜", permission=GROUP, priority=5, block=True)

wbtop_url = "https://weibo.com/ajax/side/hotSearch"

wbtop_data = []


@wbtop.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    global wbtop_data
    msg = arg.extract_plain_text().strip()
    if not wbtop_data or not msg:
        await wbtop.send("正在获取微博热搜数据中，请稍作等待(－ω－)")
        if wbtop_data:
            now_time = datetime.datetime.now()
            if now_time > wbtop_data["time"] + datetime.timedelta(minutes=5):
                data, code = await get_wbtop(wbtop_url)
                if code != 200:
                    await wbtop.finish(data, at_sender=True)
                wbtop_data = data
        else:
            data, code = await get_wbtop(wbtop_url)
            if code != 200:
                await wbtop.finish(data, at_sender=True)
            wbtop_data = data
        if not msg:
            img = await asyncio.get_event_loop().run_in_executor(
                None, gen_wbtop_pic, wbtop_data["data"]
            )
            await wbtop.send(reply(event.message_id) + img)
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 查询微博热搜"
            )
    if is_number(msg) and 0 < int(msg) <= 50:
        url = wbtop_data["data"][int(msg) - 1]["url"]
        await wbtop.send("开始截取数据...")
        img = await AsyncPlaywright.screenshot(
            url,
            f"{IMAGE_PATH}/temp/wbtop_{event.user_id}.png",
            "#pl_feed_main",
            wait_time=12
        )
        if img:
            await wbtop.send(reply(event.message_id) + img)
        else:
            await wbtop.send(reply(event.message_id) + "发生了一些错误.....")
