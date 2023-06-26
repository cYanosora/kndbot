import os
import time
import json
import random
from pathlib import Path
from datetime import datetime
from nonebot import on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupIncreaseNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupBanNoticeEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed
from services.db_context import db
from services.log import logger
from models.level_user import LevelUser
from models.ban_info import BanInfo
from models.group_info import GroupInfo
from models.group_member_info import GroupInfoUser
from utils.utils import FreqLimiter, timeremain
from utils.message_builder import image, at
from manager import Config
from manager import group_manager, plugins2settings_manager, requests_manager
from configs.path_config import IMAGE_PATH, DATA_PATH
from configs.config import NICKNAME
from .rule import group_in_rule, group_ban_rule, group_de_rule


__plugin_name__ = "群事件处理 [Hidden]"
__plugin_version__ = 0.1
__plugin_task__ = {"group_welcome": "进群欢迎", "refund_group_remind": "退群提醒"}
Config.add_plugin_config(
    "invite_manager", "quit_message", f"请获得master的白名单后再拉{NICKNAME}入群！告辞！", help_="强制拉群后进群回复的内容.."
)
Config.add_plugin_config(
    "invite_manager", "welcome_message", [f"欢迎新人，这里是{NICKNAME}，请多关照~"], help_="有新人进群的欢迎消息"
)
Config.add_plugin_config(
    "invite_manager", "flag", True, help_="被强制拉群后是否直接退出", default_value=True
)
Config.add_plugin_config(
    "invite_manager", "welcome_msg_cd", 5, help_="群欢迎消息cd[单位：秒]", default_value=5
)
Config.add_plugin_config(
    "invite_manager", "kick_msg_cd", 5, help_="退群提醒消息cd[单位：秒]", default_value=5
)
Config.add_plugin_config(
    "_task",
    "DEFAULT_GROUP_WELCOME",
    True,
    help_="被动 进群欢迎 进群默认开关状态",
    default_value=True,
)
Config.add_plugin_config(
    "_task",
    "DEFAULT_REFUND_GROUP_REMIND",
    True,
    help_="被动 退群提醒 进群默认开关状态",
    default_value=True,
)

_welc_flmt = FreqLimiter(Config.get_config("invite_manager", "welcome_msg_cd"))
_kick_flmt = FreqLimiter(Config.get_config("invite_manager", "kick_msg_cd"))


# 群员增加处理
group_increase_handle = on_notice(priority=1, rule=group_in_rule(), block=False)
# 群员减少处理
group_decrease_handle = on_notice(priority=1, rule=group_de_rule(), block=False)
# bot被群禁言处理
group_ban_handle = on_notice(priority=1, rule=group_ban_rule(), block=False)


@group_increase_handle.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    # bot入群
    if event.user_id == int(bot.self_id):
        group = await GroupInfo.get_group_info(event.group_id)
        # 群聊不存在或被强制拉群，退出该群
        if (not group or group.group_flag == 0) and Config.get_config("invite_manager", "flag"):
            try:
                msg = Config.get_config("invite_manager", "quit_message")
                if msg:
                    await bot.send_group_msg(group_id=event.group_id, message=msg)
                await bot.set_group_leave(group_id=event.group_id)
                await bot.send_private_msg(
                    user_id=int(list(bot.config.superusers)[0]),
                    message=f"触发强制入群保护，已成功退出群聊 {event.group_id}..",
                )
                logger.info(f"强制拉群或未有群信息，退出群聊 {group} 成功")
                requests_manager.remove_request("group", event.group_id)
            except Exception as e:
                logger.warning(f"强制拉群或未有群信息，退出群聊 {group} 失败 e:{e}")
                await bot.send_private_msg(
                    user_id=int(list(bot.config.superusers)[0]),
                    message=f"触发强制入群保护，退出群聊 {event.group_id} 失败..",
                )
        # 正常加入群聊
        elif event.group_id not in group_manager["group_manager"].keys():
            # 没有其它bot在群内
            other_bots = list(filter(lambda x:int(x.self_id) != bot.self_id, await GroupInfoUser.get_group_bots(event.group_id)))
            if len(other_bots) == 0: 
                # 默认群功能开关
                data = plugins2settings_manager.get_data()
                for plugin in data.keys():
                    if not data[plugin]["default_status"]:
                        group_manager.block_plugin(plugin, event.group_id)
            # 即刻更新成员信息列表
            _group_user_list = await bot.get_group_member_list(group_id=event.group_id)
            for user_info in _group_user_list:
                nickname = user_info["card"] or user_info["nickname"]
                async with db.transaction():
                    # 更新权限
                    if str(user_info["user_id"]) in bot.config.superusers:
                        await LevelUser.set_level(
                            user_info["user_id"], user_info["group_id"], 9
                        )
                    elif (
                        user_info["role"] in ["owner", "admin"]
                        and not await LevelUser.is_group_flag(user_info["user_id"], event.group_id)
                    ):
                        await LevelUser.set_level(
                            user_info["user_id"],
                            user_info["group_id"],
                            Config.get_config("admin_bot_manage", "ADMIN_DEFAULT_AUTH"),
                        )
                    # 更新群组成员信息列表
                    user = await GroupInfoUser.get_member_info(
                        user_info["user_id"], user_info["group_id"]
                    )
                    if user:
                        if user.user_name != nickname:
                            await user.update(user_name=nickname).apply()
                    else:
                        join_time = datetime.strptime(
                            time.strftime(
                                "%Y-%m-%d %H:%M:%S", time.localtime(user_info["join_time"])
                            ),
                            "%Y-%m-%d %H:%M:%S",
                        )
                        if not await GroupInfoUser.add_member_info(
                                user_info["user_id"],
                                user_info["group_id"],
                                nickname,
                                join_time,
                        ):
                            logger.warning(
                                f"用户{user_info['user_id']} 所属{user_info['group_id']} 更新失败\n"
                            )
    # 有新人入群
    else:
        # 添加新群员信息
        join_time = datetime.now()
        user_info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=event.user_id
        )
        if await GroupInfoUser.add_member_info(
            user_info["user_id"],
            user_info["group_id"],
            user_info["nickname"],
            join_time,
        ):
            logger.info(f"用户{user_info['user_id']} 所属{user_info['group_id']} 更新成功")
        else:
            logger.warning(f"用户{user_info['user_id']} 所属{user_info['group_id']} 更新失败")
        # 其它bot入群
        other_bots = list(filter(lambda x:int(x.self_id) != bot.self_id, await GroupInfoUser.get_group_bots(event.group_id)))
        if len(other_bots) > 0:
            await group_increase_handle.finish()
        # 群欢迎消息
        if _welc_flmt.check(event.group_id):
            _welc_flmt.start_cd(event.group_id)
            msg = ""
            img = ""
            at_flag = False
            custom_welcome_msg_json = (
                Path() / "data" / "custom_welcome_msg" / "custom_welcome_msg.json"
            )
            if custom_welcome_msg_json.exists():
                data = json.load(open(custom_welcome_msg_json, "r"))
                if data.get(str(event.group_id)):
                    msg = data[str(event.group_id)]
                    if msg.find("[at]") != -1:
                        msg = msg.replace("[at]", "")
                        at_flag = True
            if (DATA_PATH / "custom_welcome_msg" / f"{event.group_id}.jpg").exists():
                img = image(
                    DATA_PATH / "custom_welcome_msg" / f"{event.group_id}.jpg"
                )
            if msg or img:
                msg = msg.strip() + img
                msg = "\n" + msg if at_flag else msg
                await group_increase_handle.send(
                    "[[_task|group_welcome]]" + msg, at_sender=at_flag
                )
            else:
                msg = random.choice(Config.get_config("invite_manager", "welcome_message"))
                if msg:
                    await group_increase_handle.send(
                        "[[_task|group_welcome]]" + at(event.user_id) + msg
                        + image(random.choice(os.listdir(IMAGE_PATH / "qxz")), "qxz")
                    )
                else:
                    await group_increase_handle.send(
                        "[[_task|group_welcome]]" + at(event.user_id) + f"欢迎新人，这里是{NICKNAME}，请多关照~"
                        + image(random.choice(os.listdir(IMAGE_PATH / "qxz")), "qxz")
                    )


@group_decrease_handle.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    # bot被踢出群
    if event.sub_type == "kick_me":
        group_id = event.group_id
        operator_id = event.operator_id
        try:
            operator_name = (
                await GroupInfoUser.get_member_info(event.operator_id, event.group_id)
            ).user_name
        except AttributeError:
            operator_name = "None"
        # 若群内无其它bot
        left_bots = list(filter(lambda x:int(x.self_id) != bot.self_id, await GroupInfoUser.get_group_bots(event.group_id)))
        if left_bots == 0:
            await GroupInfo.delete_group_info(group_id)
            group_manager.delete_group(event.group_id)
        group = await GroupInfo.get_group_info(group_id)
        group_name = group.group_name if group else ""
        coffee = int(list(bot.config.superusers)[0])
        await bot.send_private_msg(
            user_id=coffee,
            message=f"****呜..一份踢出报告****\n"
                    f"我被 {operator_name}({operator_id})\n"
                    f"踢出了 {group_name}({group_id})\n"
                    f"日期：{str(datetime.now()).split('.')[0]}",
        )
        return
    # bot主动退群
    if event.user_id == int(bot.self_id):
        #其它bot一起退群
        left_bots = list(filter(lambda x:int(x.self_id) != bot.self_id, await GroupInfoUser.get_group_bots(event.group_id)))
        for each_bot in left_bots:
            try:
                await each_bot.set_group_leave(group_id=int(group_id))
                logger.info(f"bot{each_bot.self_id} 退出群聊 {group_id} 成功")
            except Exception as e:
                logger.info(f"bot{each_bot.self_id} 退出群聊 {group_id} 失败 e:{e}") 
        await GroupInfo.delete_group_info(event.group_id)
        group_manager.delete_group(event.group_id)
        return
    # 其它群员退群
    try:
        user_name = (
            await GroupInfoUser.get_member_info(event.user_id, event.group_id)
        ).user_name
    except AttributeError:
        user_name = str(event.user_id)
    if await GroupInfoUser.delete_member_info(event.user_id, event.group_id):
        logger.info(f"用户{user_name}, qq={event.user_id} 所属{event.group_id} 删除成功")
    else:
        logger.warning(f"用户{user_name}, qq={event.user_id} 所属{event.group_id} 删除失败")
    if _kick_flmt.check(event.group_id):
        _kick_flmt.start_cd(event.group_id)
        rst = ""
        if event.sub_type == "leave":
            rst = f"啊...{user_name}退群了..."
        if event.sub_type == "kick":
            operator = await bot.get_group_member_info(
                user_id=event.operator_id, group_id=event.group_id
            )
            operator_name = operator["card"] if operator["card"] else operator["nickname"]
            rst = f"{user_name}被{operator_name}送走了呢"
        try:
            await group_decrease_handle.send(f"[[_task|refund_group_remind]]{rst}")
        except ActionFailed:
            return


@group_ban_handle.handle()
async def _(bot: Bot, event: GroupBanNoticeEvent):
    group_id = event.group_id
    operator_id = event.operator_id
    duration = event.duration
    try:
        operator_name = (
            await GroupInfoUser.get_member_info(event.operator_id, event.group_id)
        ).user_name
    except AttributeError:
        operator_name = "未知"
    coffee = int(list(bot.config.superusers)[0])
    group = await GroupInfo.get_group_info(group_id)
    group_name = group.group_name if group else ""
    if BanInfo.is_ban(group_id=group_id):
        await BanInfo.unban(group_id=group_id)
    if duration != 0:
        # 将群添加进临时黑名单，防止禁言期间响应指令导致风控
        await BanInfo.ban(ban_level=9, duration=event.duration, group_id=group_id)
        # bot被禁言时，告知master，以便作出进一步的判断
        await bot.send_private_msg(
            user_id=coffee,
            message=f"****bot被禁言报告****\n"
                    f"用户：{operator_name}({operator_id})\n"
                    f"群：{group_name}({group_id})\n"
                    f"日期：{str(datetime.now()).split('.')[0]}\n"
                    f"时长：{timeremain(event.duration)}",
        )

