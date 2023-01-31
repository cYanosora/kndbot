import time
from nonebot import on_message, on_command, get_bots
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, Bot
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.permission import SUPERUSER
from services import logger
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from utils.utils import scheduler
from manager import group_manager
from models.group_member_info import GroupInfoUser
from ._config import pjsk_plugins, check_limit_time
from ._rule import check_rule
from ._model import PjskUniRecord, unibot


__plugin_name__ = "uni分布式检测 [Superuser]"
__plugin_type__ = "烧烤相关"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    检测群内是否有uni分布式的存在，防止同功能bot重复响应指令，且自动开关烧烤相关功能
    查询uni分布式            ：显示bot加的哪些群内含有uni分布式
""".strip()
__plugin_settings = {
    "cmd": ["uni分布式检测", "查询uni分布式"]
}


@run_preprocessor
async def _(matcher: Matcher, bot: Bot, event: GroupMessageEvent):
    if matcher.plugin_name not in pjsk_plugins:
        return
    unibot.starttime = time.time()
    # print('check:',unibot.starttime)
    members = await GroupInfoUser.get_group_member_id_list(event.group_id)
    # 若群内存在unibot
    try:
        next(filter(lambda x: unibot.get(x), members))
        print('真的有unibot')
        # 检查群聊烧烤功能开关
        if group_manager.get_plugin_status(matcher.plugin_name, event.group_id):
            for mod in pjsk_plugins:
                group_manager.block_plugin(mod, event.group_id)
                group_manager.block_plugin(f"{mod}:super", event.group_id)
            await bot.send_group_msg(
                group_id=event.group_id,
                message="自动检测：群内已有unibot分布式，已关闭烧烤相关功能(需再次开启请联系master)"
            )
        raise IgnoredException("群内存在unibot，忽略烧烤相关命令")
    # 若群内不存在unibot
    except:
        pass
        # # 检查群聊烧烤功能开关
        # if not group_manager.get_plugin_status(matcher.plugin_name, event.group_id):
        #     for mod in pjsk_plugins:
        #         group_manager.unblock_plugin(mod, event.group_id)
        #     await bot.send_group_msg(
        #         group_id=event.group_id,
        #         message="自动检测：群内尚未有unibot分布式，已开启烧烤相关功能(未检测成功时，请手动关闭)"
        #     )

bot_record = on_message(rule=check_rule(), permission=GROUP, priority=1, block=False)

bot_check = on_command("查询uni分布式", permission=SUPERUSER, priority=1, block=True)


@bot_record.handle()
async def record(event: GroupMessageEvent):
    # print('record:',unibot.starttime)
    if time.time() - unibot.starttime < check_limit_time:
        print(f'记录这个id:{event.user_id}')
        await PjskUniRecord.add(event.user_id)
    unibot.starttime = 0


@bot_check.handle()
async def check():
    record, sum_count = await PjskUniRecord.get_record(0.5)
    if not record:
        await bot_check.finish("当前暂无检测出uni分布式")
    if sum_count > 1000:
        [unibot.set(i) for i in record]
    result = {}
    bots = list(get_bots().values())
    for bot in bots:
        if not result.get(str(bot.self_id)):
            result[str(bot.self_id)] = []
        gl = [g["group_id"] for g in await bot.get_group_list()]
        for g in gl:
            members = await GroupInfoUser.get_group_member_id_list(g)
            for i in filter(lambda x: unibot.get(x), members):
                result[str(bot.self_id)].append((g, i))
    reply = ''
    _c = 0
    for qq in result.keys():
        reply += f'Bot({qq})可能在以下群发现unibot分布式：\n'
        for ub in result[qq]:
            _c += 1
            reply += f"群({ub[0]})内用户({ub[1]})\n"
        reply += '\n'
    reply = reply[:-1]
    if _c >= 10:
        reply = image(b64=pic2b64(text2image(reply)))
    await bot_check.finish(reply)


# # 定时检查unibot分布式
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=10,
)
async def schedule_check():
    error = ''
    try:
        # 更新可能是分布式的账号记录
        record, sum_count = await PjskUniRecord.get_record(0.5)
        if record and sum_count > 1000:
            [unibot.set(i) for i in record]
    except Exception as e:
        error += f"{e}\n"
    try:
        # 清除记录过少的账号，这些可能并非分布式
        record, sum_count = await PjskUniRecord.get_record(0.1, True)
        if record and sum_count > 300:
            [await PjskUniRecord.pop(i) for i in record]
    except Exception as e:
        error += f"{e}\n"
    if error:
        logger.info(f"自动更新unibot分布式记录出错，错误信息：{error}")
    else:
        logger.info(f"自动更新unibot分布式记录成功")


