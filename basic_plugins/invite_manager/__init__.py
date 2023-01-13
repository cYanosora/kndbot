import time
from datetime import datetime
from nonebot import on_request, on_notice
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    Bot,
    FriendRequestEvent,
    GroupRequestEvent,
    FriendAddNoticeEvent,
)
from services import logger
from configs.path_config import IMAGE_PATH
from configs.config import NICKNAME, MAIN_BOT
from models.friend_user import FriendUser
from models.group_info import GroupInfo
from manager import Config
from manager import requests_manager
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
# group_reply = on_command("入群条件", priority=1, block=True, permission=PRIVATE_FRIEND)

exists_data = {"private": {}, "group": {}}
# raw_text = f"想要邀请{NICKNAME}入群嘛？以下为目前的入群条件(虽然很长，但是不看完不接受拉群)：\n\n"\
#         f"[size=30]1：{NICKNAME}仅接受pjsk群的入群申请[/size]" \
#         f"[size=30][color=red](因为是面向pjsk玩家的bot，不聊pjsk的群可以不用再往下看了)[/color][/size]\n"\
#         f"[size=30]2：请务必确保已经得到群主或群管理的同意，入群就被T掉也别来找我[/size]\n" \
#         f"[size=30]3：出于拉群后使用体验的考量，至少邀请者本人需要熟悉{NICKNAME}的功能(见ps说明)[/size]\n" \
#         f"[size=30]4：目前一号机群太多已不再接受入群申请，要拉群请找二号机👉👉 QQ:2488024911[/size]\n" \
#         f"[size=30](二号机的好友验证问题回复 [color=red]拉群[/color] " \
#         f"即可自动通过，否则需要等待bot管理的人工验证)[/size]\n"\
#         f"[size=30]5：一定要找{NICKNAME}的bot管理申请群白名单[/size]" \
#         f"[size=30][color=red](没有白名单的话，强制拉{NICKNAME}进群是会自动退群的)[/color][/size]\n\n" \
#         f"ps:若之后发现是不满足以上条件的拉群行为将赠送退群拉黑套餐，请勿自找麻烦！" \
#         f"[color=red](比如说不是pjsk群仍说是pjsk群的)[/color]\n" \
#         f"ps:理论上拉群后{NICKNAME}由邀请者本人管理，" \
#         f"所以邀请者无论是不是群管理员都会获得{NICKNAME}的默认管理权限" \
#         f"[color=red](可以掌管功能的开关等等)[/color]\n" \
#         f"ps:关于第3点的说明，其实只要" \
#         f"[color=red]学会拉取{NICKNAME}的帮助说明图片[/color]" \
#         f"这一点不是问题。(当然得在群内才能获取)\n" \
#         f"    例如：kndhelp、knd看图help、knd签到help等等..." \
#         f"[color=red](关键是你能看懂kndhelp上面的文字说明)[/color]\n" \
#         f"ps:告知bot管理自己是否满足入群要求时，默认你已经充分了解了以上所有内容且具有拉群资格。" \
#         f"[color=red]指令格式：滴滴滴 这里是你想说的话[/color]"
path = IMAGE_PATH / "group_invite.png"
if path.exists():
    path.unlink()


@friend_reply.handle()
async def _(bot: Bot, event: FriendAddNoticeEvent):
    # 一号机自动同意好友请求并回复
    if Config.get_config("invite_manager", "AUTO_ADD_FRIEND", False) and bot.self_id == str(MAIN_BOT):
        await bot.send_private_msg(
            user_id=event.user_id,
            message="已自动通过你的好友申请啦，这里是奏宝一号机\n"
                    "咱的功能只能在群聊中使用哦\n"
                    "由于一些不可抗力因素，咱目前已经停止接受新群的邀请了~\n"
                    "如需咨询咱的master请通过指令沟通👉👉发送格式：滴滴滴 这里是你想说的话"
        )
    else:
        await bot.send_private_msg(
            user_id=event.user_id,
            message="已通过你的好友申请啦，这里是奏宝二号机\n"
                    "咱的功能只能在群聊中使用哦\n"
                    "由于一些不可抗力因素，咱目前已经停止接受新群的邀请了~\n"
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
    # 告知超级用户有bot好友申请通知
    await bot.send_private_msg(
        user_id=int(list(bot.config.superusers)[0]),
        message=f"*****一份好友申请*****\n"
        f"昵称：{nickname}({event.user_id})\n"
        f"自动同意：{'√' if Config.get_config('invite_manager', 'AUTO_ADD_FRIEND') else '×'}\n"
        f"日期：{str(datetime.now()).split('.')[0]}\n"
        f"备注：{comment}",
    )
    # 自动添加好友，更新好友信息
    if Config.get_config("invite_manager", "AUTO_ADD_FRIEND"):
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
            # try:
            #     await bot.send_private_msg(
            #         user_id=event.user_id,
            #         message=f"想要邀请我入群嘛~已经提醒{NICKNAME}的bot管理了\n"
            #         "请务必确保你已经了解所有的入群要求！\n"
            #         "若尚未阅读过入群要求，请发送：入群申请\n"
            #         "如果需要咨询bot管理员请通过指令沟通，发送格式：滴滴滴 想说的话"
            #     )
            # except ActionFailed:
            #     logger.info(
            #         f"USER {event.user_id} 关闭了临时会话功能! "
            #     )
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


# @group_reply.handle()
# async def _(bot: Bot, event: PrivateMessageEvent):
#     if _reply_flmt.check(event.user_id):
#         _reply_flmt.start_cd(event.user_id)
#         if not path.exists():
#             global text
#             img = text2image(text, padding=(20, 20), fontsize=20)
#             img.save(path)
#         reply = image(path)
#         try:
#             await bot.send_private_msg(
#                 user_id=event.user_id,
#                 message=reply
#             )
#         except ActionFailed:
#             await bot.send_private_msg(
#                 user_id=event.user_id,
#                 message=reply
#             )
#             await asyncio.sleep(3)
#             await bot.send_private_msg(
#                 user_id=int(list(bot.config.superusers)[0]),
#                 message=f"用户({event.user_id})获取拉群请求失败，请尝试主动沟通！"
#             )


# 每5分钟清空一次请求数据
@scheduler.scheduled_job(
    "interval",
    minutes=5,
)
async def _():
    global exists_data
    exists_data = {"private": {}, "group": {}}
