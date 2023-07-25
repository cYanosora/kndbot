import asyncio
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent
from configs.config import BOT_URL
from models.bag_user import BagUser
from models.group_member_info import GroupInfoUser
from services import logger
from utils.utils import scheduler
from .router import route
from .schema import EatkndRecord, EatkndToken

__plugin_name__ = "吃掉小奏宝"
__plugin_type__ = "网页游戏"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    奏宝bot的网页游戏-吃掉小奏宝， 用处只有赚金币
    指令：
        吃掉小奏宝       : 小窗内发送(要加好友)，会得到bot发给你的专属网页链接，点进去玩(再触发指令可以刷新链接)
        吃掉小奏宝       : 群聊里发送，等同戳网页链接 https://{BOT_URL}/game/eatknd/
    说明：
        如果你想要用这个功能赚金币，第一次游玩时请在小窗内触发功能，以得到属于你自己的专属游戏链接，
        点进去后浏览器会帮你记住你的用户信息，只要不是开了隐私模式或者清除了浏览器数据，
        之后都可以直接戳 https://{BOT_URL}/game/eatknd/ 继续以当前用户的信息继续游戏

        如果你不需要这个功能赚金币，可以在群里触发指令，或者戳 https://{BOT_URL}/game/eatknd/ 进行游玩即可
        不过这样你也无法上传成绩，只能纯单机

        赚取的金币每天0点发放，兑换比例：2得分=1金币，封顶100金币
        用户所在的所有群都会享有发放的每日奖励
    附加：
        考虑到bot再加娱乐功能聊天会很刷屏，对大家对bot自身都不好，所以就有了这个网页游戏
        关于网页游戏的排行榜，上面会显示你的QQ号昵称，以及你游玩时的昵称(如果你设置了的话)
        游戏的内容来自github的开源项目：吃掉小鹿乃(https://github.com/arcxingye/EatKano/)
""".strip()
__plugin_settings__ = {
    "cmd": ["网页游戏", "娱乐功能", "吃掉小奏宝"],
}

eatknd = on_command("吃掉小奏宝", aliases={"吃掉奏宝"}, priority=5, block=True)


@eatknd.handle()
async def _(event: MessageEvent):
    if isinstance(event, GroupMessageEvent):
        msgs = [
            f'http://{BOT_URL}/game/eatknd/',
        ]
        if await EatkndToken.get_user_by_id(event.user_id):
            tmp = '请将链接复制到浏览器再打开~'
        else:
            tmp = '请将链接复制到浏览器再打开，第一次游玩建议先阅读说明书再游玩~'
        msgs.append(tmp)
        for msg in msgs:
            await eatknd.send(msg)
            await asyncio.sleep(0.5)
        return
    access_key = await EatkndToken.gene_token(event.user_id)
    await eatknd.finish(f"https://{BOT_URL}/game/eatknd/{access_key}\n这是你的游玩链接~")


# 日排行榜发放奖励
@scheduler.scheduled_job(
    "cron",
    hour=23,
    minute=59,
)
async def _():
    logger.info(f"[定时任务]:每日游戏排行榜金币结算开始")
    day_cnt = await EatkndRecord.get_len('day')
    day_users = await EatkndRecord.get_list('day', num=day_cnt, is_update=True)
    for user in day_users:
        coin = user.score//2
        if coin == 0:
            continue
        user_all_groups = await GroupInfoUser.get_user_all_group(user.user_id)
        for group_id in user_all_groups:
            await BagUser.add_gold(user.user_id, group_id, coin)
            logger.info(f"[定时任务]:User {user.user_id} Group {group_id} 获取每日游戏排行榜金币 {coin}")
    logger.info(f"[定时任务]:每日游戏排行榜金币结算完成")
