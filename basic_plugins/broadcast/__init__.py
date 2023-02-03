import random
from typing import List
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot import on_command, get_bots
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from utils.utils import get_message_img
from services.log import logger
from utils.message_builder import image
from manager import group_manager
from manager import Config
import asyncio


__plugin_name__ = "超管广播 [Superuser]"
__plugin_type__ = "消息播报"
__plugin_version__ = 0.1
__plugin_superuser_usage__ = """
usage：
    指令：
        .广播 ?[消息] ?[图片]
    示例：
        .广播 你们好！
""".strip()
__plugin_settings = {
    "cmd": ["超管广播"]
}
__plugin_task__ = {"broadcast": "超管广播"}

Config.add_plugin_config(
    "_task",
    "DEFAULT_BROADCAST",
    True,
    help_="被动 广播 进群默认开关状态",
    default_value=True,
)

broadcast = on_command(".广播", aliases={'/广播'}, priority=1, permission=SUPERUSER, block=True)


@broadcast.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    img_list = get_message_img(event.json())
    rst = ""
    for img in img_list:
        rst += image(img)
    if not msg and not rst:
        await broadcast.finish("你没有要说的话嘛！", at_sender=True)
    bots = list(get_bots().values())
    _tmp_gl = []
    all_gl = {}
    # 收集可以广播的群号
    for bot in bots:
        gl = await bot.get_group_list()
        gl = [
            g["group_id"]
            for g in gl
            if await group_manager.check_group_task_status(g["group_id"], "broadcast")
        ]
        [_tmp_gl.append(g) for g in gl]
        bot_gl = [g for g in gl if g not in all_gl]
        all_gl[bot.self_id] = bot_gl.copy()
    # 协程发送广播信息
    thread_loop = asyncio.get_event_loop()
    for bot in bots:
        asyncio.run_coroutine_threadsafe(_broadcast_send(bot, all_gl[bot.self_id], msg+rst), thread_loop)


async def _broadcast_send(bot: Bot, group_lst: List[int], msg: str):
    g_cnt = len(group_lst)
    cnt = 0
    error = ""
    x = 0.25
    for g in group_lst:
        cnt += 1
        if cnt / g_cnt > x:
            await broadcast.send(f"已播报至 {int(cnt / g_cnt * 100)}% 的群聊")
            x += 0.25
        try:
            await bot.send_group_msg(group_id=g, message="来自master的广播消息\n" + msg)
            logger.info(f"GROUP {g} 投递广播成功")
        except Exception as e:
            logger.error(f"GROUP {g} 投递广播失败：{type(e)}")
            error += f"GROUP {g} 投递广播失败：{type(e)}\n"
        # 自主休息4~8秒后再发送到下一个群，防止消息风控
        await asyncio.sleep(random.randint(4, 8))
    await broadcast.send(f"已播报至 100% 的群聊")
    if error:
        await broadcast.send(f"播报时错误：{error}")