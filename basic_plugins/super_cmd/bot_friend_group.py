from typing import Tuple
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.params import Command, CommandArg
from nonebot.adapters.onebot.v11 import Bot, Message, ActionFailed
from models.level_user import LevelUser
from models.group_info import GroupInfo
from manager import Config
from manager import requests_manager
from utils.utils import is_number
from utils.message_builder import image


__plugin_name__ = "好友群组管理 [Superuser]"
__plugin_type__ = "信息管理"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    显示所有好友群组
    指令：
        查看所有[好友/群组]
        同意[好友/群组]请求 [id]
        拒绝[好友/群组]请求 [id]
        查看[所有/好友/群组]请求
        清空[所有/好友/群组]请求
""".strip()
__plugin_settings__ = {
    "cmd": ["好友群组管理"]
}


cls_group = on_command(
    "查看所有群组", rule=to_me(), permission=SUPERUSER, priority=1, block=True
)
cls_friend = on_command(
    "查看所有好友", rule=to_me(), permission=SUPERUSER, priority=1, block=True
)

friend_handle = on_command(
    "同意好友请求", aliases={"拒绝好友请求"}, permission=SUPERUSER, priority=1, block=True
)

group_handle = on_command(
    "同意群组请求", aliases={"拒绝群组请求"}, permission=SUPERUSER, priority=1, block=True
)

clear_request = on_command(
    "清空所有请求", aliases={"清空好友请求", "清空群组请求"}, permission=SUPERUSER, priority=1, block=True
)

cls_request = on_command(
    "查看所有请求", aliases={"查看好友请求", "查看群组请求"}, permission=SUPERUSER, priority=1, block=True
)


@cls_group.handle()
async def _(bot: Bot):
    gl = await bot.get_group_list()
    msg = ["{group_id} {group_name}".format_map(g) for g in gl]
    msg = "\n".join(msg)
    msg = f"bot:{bot.self_id}\n| 群号 | 群名 | 共{len(gl)}个群\n" + msg
    await cls_group.send(msg)


@cls_friend.handle()
async def _(bot: Bot):
    gl = await bot.get_friend_list()
    msg = ["{user_id} {nickname}".format_map(g) for g in gl]
    msg = "\n".join(msg)
    msg = f"| QQ号 | 昵称 | 共{len(gl)}个好友\n" + msg
    await cls_friend.send(msg)


@friend_handle.handle()
async def _(bot: Bot, cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()):
    cmd = cmd[0]
    id_ = arg.extract_plain_text().strip()
    if is_number(id_):
        id_ = int(id_)
        if cmd[:2] == "同意":
            if await requests_manager.approve(bot, id_, "private"):
                await friend_handle.send("同意好友请求成功..")
            else:
                await friend_handle.send("同意好友请求失败，可能是未找到此id的请求..")
        else:
            if await requests_manager.refused(bot, id_, "private"):
                await friend_handle.send("拒绝好友请求成功..")
            else:
                await friend_handle.send("拒绝好友请求失败，可能是未找到此id的请求..")
    else:
        await friend_handle.send("id必须为纯数字！")


@group_handle.handle()
async def _(bot: Bot, cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()):
    cmd = cmd[0]
    id_ = arg.extract_plain_text().strip()
    if is_number(id_):
        id_ = int(id_)
        if cmd[:2] == "同意":
            rid = requests_manager.get_group_id(id_)
            uid = requests_manager.get_group_uid(id_)
            if rid:
                await friend_handle.send("同意群组请求成功..")
                if await GroupInfo.get_group_info(rid):
                    await GroupInfo.set_group_flag(rid, 1)
                else:
                    try:
                        group_info = await bot.get_group_info(group_id=rid)
                    except ActionFailed:
                        group_info = {
                            'group_id': rid,
                            'group_name': '未知群聊',
                            'max_member_count': 0,
                            'member_count': 0
                        }
                    await GroupInfo.add_group_info(
                        rid,
                        group_info["group_name"],
                        group_info["max_member_count"],
                        group_info["member_count"],
                        1
                    )
                await LevelUser.set_level(
                    uid,
                    rid,
                    Config.get_config("admin_bot_manage", "ADMIN_DEFAULT_AUTH"),
                    1
                )
                await requests_manager.approve(bot, id_, "group")
            else:
                await friend_handle.send("同意群组请求失败，可能是未找到此id的请求..")
        else:
            if await requests_manager.refused(bot, id_, "group"):
                await friend_handle.send("拒绝群组请求成功..")
            else:
                await friend_handle.send("拒绝群组请求失败，可能是未找到此id的请求..")
    else:
        await friend_handle.send("id必须为纯数字！")


@cls_request.handle()
async def _(cmd: Tuple[str, ...] = Command()):
    cmd = cmd[0]
    _str = ""
    if '好友' in cmd:
        type_list = ['private']
    elif '群组' in cmd:
        type_list = ['group']
    else:
        type_list = ["private", "group"]
    for type_ in type_list:
        msg = await requests_manager.show(type_)
        if msg:
            _str += image(b64=msg)
        else:
            _str += "没有任何好友请求.." if type_ == "private" else "没有任何群组请求.."
        if len(type_list) > 1:
            _str += '\n--------------------\n'
    await cls_request.send(Message(_str))


@clear_request.handle()
async def _(arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if '好友' in msg:
        _type = 'private'
    elif '群组' in msg:
        _type = 'group'
    else:
        _type = None
    requests_manager.clear(_type)
    await clear_request.send(f"已清空所有{msg[2:4]}请求..")
