import re
from configs.config import NICKNAME
from .group_user_checkin import (
    group_user_check_in,
    group_user_check,
    group_impression_rank,
    impression_rank,
    check_in_all,
    setlevel, move_user_data,
    group_user_recheck_in,
    recheck_in_all
)
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.permission import GROUP
from utils.message_builder import image, reply
from nonebot import on_command
from utils.utils import scheduler
from nonebot.params import CommandArg
from pathlib import Path
from configs.path_config import DATA_PATH
from services.log import logger
from .utils import clear_sign_data_pic
from utils.utils import is_number
from nonebot.adapters.onebot.v11 import Bot
try:
    import ujson as json
except ModuleNotFoundError:
    import json

__plugin_name__ = "签到"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    每日签到(不同群好感度数据不共享)
    不是很懂有多大意义，但和小奏的 随机文本回复 功能有一定关联 
    至少你还可以视好感度增长多少为今日人品的一种体现（嗯！OvO
    指令：
        签到 ?[all]                   : all代表签到所有群，但不显示签到结果
        补签 ?[all]                   : all代表补签所有群，默认使用全部拥有的补签卡
        我的签到/好感度                 : 查看群内自己的好感度
        好感度排行                        : 查看群内好感度排行
        好感度总排行 ?[屏蔽我][显示我]       : 不带参数时，查看所有群好感度排行
        设置好感度 [数字]                  : 将好感度等级固定为某等级(必须低于原等级，设为-1时恢复原等级)(用于触发低等级随机回复文案)
        转移好感度数据/转移好感 [群id]       : 不带群id时，将自己好感度最高的群数据与当前群进行交换; 有参数时，交换指定群号的数据
    注意：
        签到时默认有 3% 概率 ×2
        本功能的金币目前仅能在 '商店' 内使用
        这部分功能还有很——多——坑——要填，但我摸了，反正也没人需要:D 
""".strip()
__plugin_settings__ = {
    "cmd": ["签到", "每日签到"],
}

__plugin_configs__ = {
    "MAX_SIGN_GOLD": {"value": 200, "help": "签到好感度加成额外获得的最大金币数", "default_value": 200},
    "SIGN_CARD1_PROB": {
        "value": 0.2,
        "help": "签到好感度双倍加持卡Ⅰ掉落概率",
        "default_value": 0.2
    },
    "SIGN_CARD2_PROB": {
        "value": 0.09,
        "help": "签到好感度双倍加持卡Ⅱ掉落概率",
        "default_value": 0.09,
    },
    "SIGN_CARD3_PROB": {
        "value": 0.05,
        "help": "签到好感度双倍加持卡Ⅲ掉落概率",
        "default_value": 0.05,
    },
    "RESIGN_CARD_PROB": {
        "value": 0.025,
        "help": "补签卡掉落概率",
        "default_value": 0.025,
    },
}


_file = Path(f"{DATA_PATH}/not_show_sign_rank_user.json")
try:
    data = json.load(open(_file, "r", encoding="utf8"))
except (FileNotFoundError, ValueError, TypeError):
    data = {"0": []}

sign = on_command("签到", priority=5, permission=GROUP, block=True)
resign = on_command("补签", priority=5, permission=GROUP, block=True)
my_sign = on_command("我的签到", aliases={"好感度"}, priority=5, permission=GROUP, block=True)
sign_rank = on_command(
    cmd="好感度排行",
    aliases={"签到排行", "好感排行", "好感度排名", "签到排名", "好感排名"},
    priority=5,
    permission=GROUP,
    block=True,
)
total_sign_rank = on_command(
    "签到总排行", aliases={"好感度总排行", "好感度总排名", "签到总排名"}, priority=5, block=True
)
change_rank = on_command(cmd="设置好感度", aliases={"设置好感", "设置好感等级"}, priority=5, permission=GROUP, block=True)
change_history_rank = on_command(cmd="转移好感度数据", aliases={"转移好感", "转移好感数据"}, priority=5, permission=GROUP, block=True)


@sign.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    opt = arg.extract_plain_text().strip()
    rule = r"^[!?.,~！？。，~-—]*$"
    if opt == "all":
        await check_in_all(bot, event)
    elif not opt or re.search(rule, opt):
        sign_pic = await group_user_check_in(bot, event)
        await sign.send(sign_pic, at_sender=True)


@resign.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    opt = arg.extract_plain_text().strip()
    rule = r"^[!?.,~！？。，~-—]*$"
    if not opt or opt != "all" or re.search(rule, opt):
        resign_reply = await group_user_recheck_in(bot, event)
        await resign.send(resign_reply, at_sender=True)
    if opt == "all":
        await recheck_in_all(bot, event)


@my_sign.handle()
async def _(event: GroupMessageEvent):
    nickname = event.sender.card or event.sender.nickname
    await my_sign.send(
        await group_user_check(nickname, event.user_id, event.group_id),
        at_sender=True,
    )


@sign_rank.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    num = arg.extract_plain_text().strip()
    if is_number(num) and 51 > int(num) > 10:
        num = int(num)
    else:
        num = 10
    await sign_rank.send("请稍等..正在整理数据...")
    _image = await group_impression_rank(event.group_id, num)
    if _image:
        await sign_rank.send(reply(event.message_id) + image(b64=_image.pic2bs4()))
    else:
        await sign_rank.send("获取签到排行出错了，请稍后再试...")


@total_sign_rank.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await total_sign_rank.send("请稍等..正在整理数据...")
        await total_sign_rank.send(reply(event.message_id) + image(b64=await impression_rank(0, data)))
    elif msg in ["屏蔽我"]:
        if event.user_id in data["0"]:
            await total_sign_rank.finish("您已经在屏蔽名单中了，请勿重复添加！", at_sender=True)
        data["0"].append(event.user_id)
        await total_sign_rank.send("设置成功，您不会出现在签到总榜中！", at_sender=True)
    elif msg in ["显示我"]:
        if event.user_id not in data["0"]:
            await total_sign_rank.finish("您不在屏蔽名单中！", at_sender=True)
        data["0"].remove(event.user_id)
        await total_sign_rank.send("设置成功，签到总榜将会显示您的头像名称以及好感度！", at_sender=True)
    with open(_file, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@change_rank.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not is_number(msg):
        await change_rank.finish("好感度必须是数字！", at_sender=True)
    level = int(msg) if int(msg) >= 0 else -1
    if await setlevel(event.user_id, event.group_id, level):
        if level == -1:
            await change_rank.finish(f"已将您在此群的好感度等级恢复默认！", at_sender=True)
            logger.info(f"USER {event.user_id} GROUP {event.group_id} 恢复默认好感等级")
        else:
            await change_rank.finish(f"设置成功，{NICKNAME}在此群对您的好感度等级将固定为{level}", at_sender=True)
            logger.info(f"USER {event.user_id} GROUP {event.group_id} 设置好感等级{level}")
    else:
        await change_rank.finish(f"设置失败，数字不能大于您目前在此群的好感度等级！", at_sender=True)


@change_history_rank.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        if is_number(msg):
            try:
                await move_user_data(event.user_id, event.group_id, int(msg))
                await change_history_rank.finish(f"你的用户数据转移完毕", at_sender=True)
                logger.info(f"USER {event.user_id} GROUP {event.group_id} 转移好感数据")
            except ValueError:
                await change_history_rank.finish(f"请检查输入的群号！你可能并不在群内！", at_sender=True)
        else:
            await change_history_rank.finish("群号只能是数字", at_sender=True)
    else:
        try:

            await move_user_data(event.user_id, event.group_id)
            await change_history_rank.finish("你的用户数据转移完毕", at_sender=True)
            logger.info(f"USER {event.user_id} GROUP {event.group_id} 转移好感数据")
        except ValueError:
            await change_history_rank.finish(f"请检查输入的群号！你可能并不在群内！", at_sender=True)


@scheduler.scheduled_job(
    "interval",
    hours=1,
)
async def _():
    try:
        clear_sign_data_pic()
        logger.info("清理日常签到图片数据数据完成....")
    except Exception as e:
        logger.error(f"清理日常签到图片数据数据失败..{type(e)}: {e}")
