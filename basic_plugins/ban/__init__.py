from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, Message, Bot
from nonebot.params import CommandArg, Command
from nonebot import on_command
from models.ban_info import BanInfo
from models.friend_user import FriendUser
from models.level_user import LevelUser
from typing import Tuple, Optional, Union
from manager import Config, plugins2settings_manager
from utils.utils import get_message_at, is_number
from configs.config import NICKNAME
from nonebot.permission import SUPERUSER
from .data_source import parse_ban_time, a_ban
from services.log import logger


__plugin_name__ = "拉黑用户 [Admin]"
__plugin_type__ = "用户管理"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    将用户拉入或拉出黑名单
    指令:
        .ban [at] ?[小时] ?[分钟]         :拉黑某用户
        .unban [at] ?[小时] ?[分钟]       :解禁某用户
    示例:
        .ban @某用户          ：将用户永久拉黑
        .ban @某用户 6        ：将用户拉黑6小时
        .ban @某用户 2 10     ：将用户拉黑2小时10分钟
        .unban @某用户        ：将用户解禁
""".strip()
__plugin_superuser_usage__ = """
superuser_usage：
    跨群ban，用于master使用
    指令：
        .B [at/qq] ?[群号] ?[功能名] ?[时间] :封禁
        .UB [at/qq] ?[群号] ?[功能名]       :解禁
    示例：
        .B @user                    ：对此艾特用户进行全群封禁
        .B 1919810                  ：对此QQ用户进行全群封禁
        .B 1919810 -1     签到       ：此QQ用户将<无法>再于<任何群>内使用<签到>功能
        .B 1919810 -1     签到 2 5   ：此QQ用户将<在2小时5分钟内>再于<任何群>内使用<签到>功能
        .B 1919810 114514 签到       ：此QQ用户将<无法>再于<此群>内使用<签到>功能
        .B 1919810 114514 签到 2 5   ：此QQ用户将<无法>再于<此群>内使用<签到>功能
""".strip()
__plugin_settings__ = {
    "admin_level": Config.get_config("ban", "BAN_LEVEL"),
    "cmd": ["拉黑用户", "ban"]
}
__plugin_configs__ = {
    "BAN_LEVEL [LEVEL]": {
        "value": 2,
        "help": "ban/unban所需要的管理员权限等级",
        "default_value": 2
    }
}


ban = on_command(
    ".ban",
    aliases={".unban", "/ban", "/unban"},
    priority=3,
    block=True,
)

super_ban = on_command(
    ".B",
    aliases={"/B", ".UB", "/UB"},
    permission=SUPERUSER,
    priority=1,
    block=True
)


@ban.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    cmd: Tuple[str, ...] = Command(),
    arg: Message = CommandArg()
):
    cmd = cmd[0]
    result = ""
    qq = get_message_at(event.json())
    if qq:
        qq = qq[0]
        user_name = await bot.get_group_member_info(group_id=event.group_id, user_id=qq)
        user_name = user_name['card'] or user_name['nickname']
        msg = arg.extract_plain_text().strip()
        time = parse_ban_time(msg)
        if isinstance(time, str):
            await ban.finish(time, at_sender=True)
        # 拉黑
        if cmd in [".ban", "/ban"]:
            if (
                await LevelUser.get_user_level(event.user_id, event.group_id)
                <= await LevelUser.get_user_level(qq, event.group_id)
                and str(event.user_id) not in bot.config.superusers
            ):
                await ban.finish(
                    f"您的权限等级比对方低或相等, {NICKNAME}不能为您使用此功能！",
                    at_sender=True,
                )
            result = await a_ban(qq, time, user_name, event)
        # 解禁
        else:
            if (
                await BanInfo.check_ban_level(
                    qq, await LevelUser.get_user_level(event.user_id, event.group_id)
                )
                and str(event.user_id) not in bot.config.superusers
            ):
                await ban.finish(
                    f"拉黑 {user_name} 的管理员权限比您高，您无法解除黑名单！", at_sender=True
                )
            flag = await BanInfo.unban(qq)
            flag = await BanInfo.unban(qq, event.group_id) or flag
            if flag:
                logger.info(
                    f"USER {event.user_id} GROUP {event.group_id} 将 USER {qq} 解禁"
                )
                result = f"已经把 {user_name} 从黑名单中删除了！"
            else:
                result = f"{user_name} 并不在黑名单啊？"
    else:
        await ban.finish("嗯...？你有艾特谁吗？", at_sender=True)
    await ban.send(result, at_sender=True)


@super_ban.handle()
async def _(
        bot: Bot,
        event: MessageEvent,
        cmd: Tuple[str, ...] = Command(),
        arg: Message = CommandArg()
):
    params = arg.extract_plain_text().strip().split()
    qq = None
    user_name = "未知"
    if isinstance(event, GroupMessageEvent):
        qq = get_message_at(event.json())
        if qq:
            qq = int(qq[0])
            user = await bot.get_group_member_info(group_id=event.group_id, user_id=qq)
            user_name = user["card"] or user["nickname"]
    if not qq:
        qq = params[0]
        if is_number(qq):
            qq = int(qq[0])
            params = params[1:]
            user_name = await FriendUser.get_user_name(qq)
        else:
            await super_ban.finish('输入的QQ号必须为数字')

    group = None
    plugin = None
    time = -1
    try:
        group, plugin, time = parse_params(*params)
    except TypeError as e:
        await super_ban.finish(str(e))
    except Exception:
        await super_ban.finish('出错了，请检查参数是否输入正确')
    if cmd[0] in [".B", "/B"]:
        if plugin:
            if not await BanInfo.ban_plugin(plugin, 9, time, qq, group):
                await BanInfo.unban_plugin(plugin, qq, group)
                await BanInfo.ban_plugin(plugin, 9, time, qq, group)
            await super_ban.finish(
                f"{user_name}({qq}) 群组({group})"
                f"功能({plugin})拉入黑名单(时长:{time if time != -1 else '永久'})！"
            )
        else:
            if not await BanInfo.ban(9, time, qq, group):
                await BanInfo.unban(qq, group)
                await BanInfo.ban(9, time, qq, group)
            await super_ban.finish(
                f"{user_name}({qq}) 群组({group})拉入黑名单(时长:{time if time != -1 else '永久'})！"
            )
    else:
        if plugin:
            await BanInfo.unban_plugin(plugin, qq, group)
            await super_ban.finish(
                f"{user_name}({qq}) 功能({plugin})解除黑名单！"
            )
        else:
            await BanInfo.unban(qq, group)
            await super_ban.finish(
                f"{user_name}({qq}) 群组({group})解除黑名单！"
            )


def parse_params(
    group: Optional[str] = None,
    plugin:  Optional[str] = None,
    hour:  Optional[str] = None,
    minute:  Optional[str] = None,
    *args
) -> Tuple[Union[None, str], Union[None, str], int]:
    if group is not None:
        if not is_number(group):
            raise TypeError('群号必须为数字')
        else:
            group = int(group)
    if plugin is not None:
        plugin = plugins2settings_manager.get_plugin_module(plugin)
        if not plugin:
            raise TypeError('找不到对应的插件')
    time = 0
    hour = hour if hour is not None else 0
    minute = minute if minute is not None else 0
    if not is_number(hour):
        raise TypeError('时间必须为数字')
    if not is_number(minute):
        raise TypeError('时间必须为数字')
    time += float(hour) * 3600
    time += float(minute) * 60
    time = int(time) if int(time) != 0 else -1
    return group, plugin, time

