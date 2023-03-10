import asyncio
import re
import time
from datetime import datetime
from nonebot import on_request, on_notice, on_command
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    Bot,
    FriendRequestEvent,
    GroupRequestEvent,
    FriendAddNoticeEvent, PRIVATE_FRIEND, PrivateMessageEvent,
)
from services import logger
from configs.config import NICKNAME, MAIN_BOT, SUB_BOT, AUX_BOT, EXT_BOT
from models.friend_user import FriendUser
from models.group_info import GroupInfo
from manager import Config
from manager import requests_manager
from utils.message_builder import image
from utils.utils import scheduler, FreqLimiter
from .rule import friend_request_rule, friend_reply_rule, group_request_rule

__plugin_name__ = "好友群聊处理请求 [Hidden]"
__plugin_version__ = 0.1
Config.add_plugin_config(
    "invite_manager",
    "AUTO_ADD_FRIEND",
    True,
    help_="是否自动同意好友添加",
    default_value=True
)


_reply_flmt = FreqLimiter(300)
friend_req = on_request(priority=5, block=True, rule=friend_request_rule())
group_req = on_request(priority=5, block=True, rule=group_request_rule())
friend_reply = on_notice(priority=5, block=False, rule=friend_reply_rule())
group_reply = on_command("入群条件", aliases={"入群申请", "拉群"}, priority=1, block=True, permission=PRIVATE_FRIEND)

exists_data = {"private": {}, "group": {}}


@friend_reply.handle()
async def _(bot: Bot, event: FriendAddNoticeEvent):
    # 一号机自动同意好友请求并回复
    if bot.self_id == str(MAIN_BOT):
        await bot.send_private_msg(
            user_id=event.user_id,
            message="已通过你的好友申请啦，这里是奏宝一号机\n"
                    "咱的大部分功能只能在群聊中使用哦\n"
                    "由于一些不可抗力因素，咱目前已经停止接受新群的邀请了~\n"
                    "但如果需要拉群，请先发送 入群条件 获取当前的拉群注意事项\n"
                    "了解注意事项后可以告诉master你想拉群，当开放了新bot时会主动联系你！\n"
                    "如果需要拉群，并且是pjsk群(必须)，那么请找四号机3630133726(好友验证填 拉群)\n"
                    "如需咨询咱的master请通过指令沟通👉👉发送格式：滴滴滴 这里是你想说的话"
        )
    # 二号机自动同意好友请求并回复
    elif bot.self_id == str(SUB_BOT):
        await bot.send_private_msg(
            user_id=event.user_id,
            message="已通过你的好友申请啦，这里是奏宝二号机\n"
                    "咱的大部分功能只能在群聊中使用哦\n"
                    "由于一些不可抗力因素，咱目前已经停止接受新群的邀请了~\n"
                    "但如果需要拉群，请先发送 入群条件 获取当前的拉群注意事项\n"
                    "了解注意事项后可以告诉master你想拉群，当开放了新bot时会主动联系你！\n"
                    "如果需要拉群，并且是pjsk群(必须)，那么请找四号机3630133726(好友验证填 拉群)\n"
                    "如需咨询咱的master请务必使用指令沟通👉👉发送格式：滴滴滴 这里是你想说的话"
        )
    # 三号机验证后同意好友请求并回复
    elif bot.self_id == str(AUX_BOT):
        await bot.send_private_msg(
            user_id=event.user_id,
            message="已通过你的好友申请啦，这里是奏宝三号机\n"
                    "咱的大部分功能只能在群聊中使用哦\n"
                    "由于一些不可抗力因素，咱目前已经停止接受新群的邀请了~\n"
                    "但如果需要拉群，请先发送 入群条件 获取当前的拉群注意事项\n"
                    "了解注意事项后可以告诉master你想拉群，当开放了新bot时会主动联系你！\n"
                    "如果需要拉群，并且是pjsk群(必须)，那么请找四号机3630133726(好友验证填 拉群)\n"
                    "如需咨询咱的master请务必使用指令沟通👉👉发送格式：滴滴滴 这里是你想说的话"
        )
    elif bot.self_id == str(EXT_BOT):
        await bot.send_private_msg(
            user_id=event.user_id,
            message="已通过你的好友申请啦，这里是奏宝四号机\n"
                    "咱的大部分功能只能在群聊中使用哦\n"
                    "如果需要拉群，请先发送 入群条件 获取当前的拉群注意事项\n"
                    "如需咨询咱的master请务必使用指令沟通👉👉发送格式：滴滴滴 这里是你想说的话"
        )


@friend_req.handle()
async def _(bot: Bot, event: FriendRequestEvent):
    global exists_data
    # 5分钟内不接受重复申请
    if exists_data["private"].get(f"{event.self_id}_{event.user_id}"):
        if time.time() - exists_data["private"][f"{event.self_id}_{event.user_id}"] < 60 * 5:
            return
    exists_data["private"][f"{event.self_id}_{event.user_id}"] = time.time()
    user = await bot.get_stranger_info(user_id=event.user_id)
    nickname = user["nickname"]
    sex = user["sex"]
    age = str(user["age"])
    comment = event.comment
    # 自动添加好友，更新好友信息
    flag = True
    if Config.get_config("invite_manager", "AUTO_ADD_FRIEND") and bot.self_id != str(EXT_BOT):
        await bot.set_friend_add_request(flag=event.flag, approve=True)
        await FriendUser.add_friend_info(user["user_id"], user["nickname"])
    # 好友验证
    else:
        flag = True if re.search('拉.*群', comment) else False
        # 验证通过
        if flag:
            await bot.set_friend_add_request(flag=event.flag, approve=True)
            await FriendUser.add_friend_info(user["user_id"], user["nickname"])
        # 添加到请求管理器
        else:
            requests_manager.add_request(
                event.user_id,
                "private",
                event.flag,
                nickname=nickname,
                sex=sex,
                age=age,
                comment=comment
            )
    # 告知超级用户有bot好友申请通知
    await bot.send_private_msg(
        user_id=int(list(bot.config.superusers)[0]),
        message=f"*****一份好友申请*****\n"
        f"昵称：{nickname}({event.user_id})\n"
        f"自动同意：{'√' if Config.get_config('invite_manager', 'AUTO_ADD_FRIEND') and flag else '×'}\n"
        f"日期：{str(datetime.now()).split('.')[0]}\n"
        f"备注：{comment}",
    )


@group_req.handle()
async def _(bot: Bot, event: GroupRequestEvent):
    global exists_data
    # 当有群聊邀请申请时
    if event.sub_type == "invite":
        # 当邀请人是超级用户时，直接加群，同时添加群认证
        if str(event.user_id) in bot.config.superusers:
                if await GroupInfo.get_group_info(event.group_id):
                    await GroupInfo.set_group_flag(event.group_id, 1)
                else:
                    try:
                        group_info = await bot.get_group_info(group_id=event.group_id)
                    except ActionFailed:
                        group_info = {
                            'group_id': event.group_id,
                            'group_name': '未知群聊',
                            'max_member_count': 0,
                            'member_count': 0
                        }
                    await GroupInfo.add_group_info(
                        group_info["group_id"],
                        group_info["group_name"],
                        group_info["max_member_count"],
                        group_info["member_count"],
                        1,
                    )
                await bot.set_group_add_request(
                    flag=event.flag, sub_type="invite", approve=True
                )
        # 若邀请人不为超级用户，通知超级用户有入群申请
        else:
            user = await bot.get_stranger_info(user_id=event.user_id)
            sex = user["sex"]
            age = str(user["age"])
            # 5分钟内不重复接受入群请求
            if exists_data["group"].get(f"{event.self_id}_{event.user_id}:{event.group_id}"):
                if (
                    time.time()
                    - exists_data["group"][f"{event.self_id}_{event.user_id}:{event.group_id}"]
                    < 300
                ):
                    return
            exists_data["group"][f"{event.self_id}_{event.user_id}:{event.group_id}"] = time.time()
            nickname = await FriendUser.get_user_name(event.user_id)
            await bot.send_private_msg(
                user_id=int(list(bot.config.superusers)[0]),
                message=f"*****一份入群申请*****\n"
                f"申请人：{nickname}({event.user_id})\n"
                f"群聊：{event.group_id}\n"
                f"邀请日期：{str(datetime.now()).split('.')[0]}",
            )
            if bot.self_id == str(EXT_BOT):
                try:
                    await bot.send_private_msg(
                        user_id=event.user_id,
                        message=f"想要邀请我入群嘛~已经提醒{NICKNAME}的bot管理了\n"
                        "请务必确保你已经了解所有的入群要求！\n"
                        "若尚未阅读过入群要求，请发送：入群条件\n"
                        "如果需要咨询咱的master请通过务必使用指令沟通，发送格式：滴滴滴 想说的话"
                    )
                except ActionFailed:
                    logger.info(
                        f"USER {event.user_id} 关闭了临时会话功能! "
                    )
            try:
                group_name = (await bot.get_group_info(group_id=event.group_id))["group_name"]
            except ActionFailed:
                group_name = '未知群聊'
            requests_manager.add_request(
                event.user_id,
                "group",
                event.flag,
                invite_group=event.group_id,
                nickname=nickname,
                sex=sex,
                age=age,
                group_name=group_name
            )


@group_reply.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    if _reply_flmt.check(event.user_id):
        _reply_flmt.start_cd(event.user_id)
        reply = image('other/group_reply.png')
        try:
            await bot.send_private_msg(
                user_id=event.user_id,
                message=reply
            )
        except ActionFailed:
            await bot.send_private_msg(
                user_id=event.user_id,
                message=reply
            )
            await asyncio.sleep(3)
            await bot.send_private_msg(
                user_id=int(list(bot.config.superusers)[0]),
                message=f"用户({event.user_id})获取拉群请求失败，请尝试主动沟通！"
            )
        else:
            await bot.send_private_msg(
                user_id=int(list(bot.config.superusers)[0]),
                message=f"用户({event.user_id})正在阅读入群条件中"
            )


# 每5分钟清空一次请求数据
@scheduler.scheduled_job(
    "interval",
    minutes=5,
)
async def _():
    global exists_data
    exists_data = {"private": {}, "group": {}}
