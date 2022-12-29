import time
import datetime
from typing import Union
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor, run_postprocessor, IgnoredException
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    GroupMessageEvent,
    PokeNotifyEvent,
    PrivateMessageEvent,
    Event,
)
from models.ban_info import BanInfo
from models.level_user import LevelUser
from utils.message_builder import at
from utils.utils import is_number, timeremain
from manager import (
    Config,
    plugins2settings_manager,
    admin_manager,
    group_manager,
    plugins_manager,
    plugins2cd_manager,
    plugins2block_manager,
    plugins2count_manager,
)
from ._utils import (
    ignore_module,
    send_msg,
    init_rst,
    _flmt,
    _flmt_c,
    _flmt_g,
    _flmt_b,
    oppose_count_modules,
    oppose_cd_modules,
)


# 群聊触发命令检测
@run_preprocessor
async def _(matcher: Matcher, bot: Bot, event: Event):
    try:
        if (isinstance(event, PrivateMessageEvent) and
            matcher.plugin_name not in ignore_module and
            str(event.user_id) not in bot.config.superusers
        ):
            raise IgnoredException("私聊触发命令被忽略")
    except AttributeError:
        pass


# 权限检测
@run_preprocessor
async def _(matcher: Matcher, bot: Bot, event: Event):
    # 不是消息或戳一戳的事件，以及优先级在[1,2,100]的响应器，master触发的指令都不需要接受预处理
    if (
        not isinstance(event, MessageEvent)
        and not isinstance(event, PokeNotifyEvent)
        or str(event.user_id) in bot.config.superusers
        or matcher.priority in [1, 2, 100]
    ):
        return
    # 群黑名单检测 群总开关检测(group_manager)
    if isinstance(event, GroupMessageEvent) or isinstance(event, PokeNotifyEvent):
        try:
            if (
                group_manager.get_group_level(event.group_id) < 0
                and str(event.user_id) not in bot.config.superusers
            ):
                raise IgnoredException("群黑名单")
            if not group_manager.check_group_bot_status(event.group_id):
                try:
                    # 若命令为开启bot总开关
                    if str(event.get_message()) in Config.get_config(
                        "admin_bot_manage", "WAKEUP_BOT_CMD", ['起来工作', '唤醒']
                    ):
                        return
                except ValueError:
                    raise IgnoredException("群功能总开关关闭状态")
        except AttributeError:
            pass
    module = matcher.plugin_name
    # 管理员插件权限检测(admin_manager, LevelUser)
    if module in admin_manager.keys():
        if isinstance(event, GroupMessageEvent) or isinstance(event, PokeNotifyEvent):
            if (
                not await LevelUser.check_level(
                    event.user_id,
                    event.group_id,
                    admin_manager.get_plugin_level(module),
                )
                and admin_manager.get_plugin_level(module) > 0
            ):
                try:
                    if _flmt.check(event.user_id):
                        _flmt.start_cd(event.user_id)
                        await bot.send_group_msg(
                            group_id=event.group_id,
                            message=f"{at(event.user_id)}你的权限不足喔，该功能需要的权限等级："
                            f"{admin_manager.get_plugin_level(module)}",
                        )
                except ActionFailed:
                    pass
                raise IgnoredException("权限不足")
    # 通用插件权限、开关状态检测(plugins2info_dict,group_manager)
    plugins2info_dict = plugins2settings_manager.get_data()
    if module in plugins2info_dict.keys():
        # 群消息(包括戳一戳)判断
        if isinstance(event, GroupMessageEvent) or isinstance(event, PokeNotifyEvent):
            # 群权限等级不够
            if plugins2info_dict[module]["level"] > group_manager.get_group_level(event.group_id):
                try:
                    if _flmt_g.check(event.user_id) and module not in ignore_module:
                        _flmt_g.start_cd(event.user_id)
                        await bot.send_group_msg(
                            group_id=event.group_id, message="群权限不足，无法使用此功能"
                        )
                except ActionFailed:
                    pass
                raise IgnoredException("群权限不足")
            # 群插件被管理禁用(无提醒消息)
            if not group_manager.get_plugin_status(module, event.group_id):
                # try:
                #     if module not in ignore_module and _flmt_s.check(
                #         event.group_id
                #     ):
                #         _flmt_s.start_cd(event.group_id)
                #         # await bot.send_group_msg(
                #         #     group_id=event.group_id, message="群管关闭了该功能"
                #         # )
                # except ActionFailed:
                #     pass
                raise IgnoredException("群管关闭了该功能")
            # 群插件被超管禁用(无提醒消息)
            if not group_manager.get_plugin_status(module, event.group_id, True):
                # try:
                #     if (
                #         _flmt_s.check(event.group_id)
                #         and module not in ignore_module
                #     ):
                #         _flmt_s.start_cd(event.group_id)
                #         await bot.send_group_msg(
                #             group_id=event.group_id, message="超管关闭了该功能"
                #         )
                # except ActionFailed:
                #     pass
                raise IgnoredException("超管关闭了该功能")
            # 群聊禁用，功能维护
            if (
                not plugins_manager.get_plugin_status(module, block_type="group")
                or not plugins_manager.get_plugin_status(module, block_type="all")
            ):
                try:
                    if _flmt_c.check(event.group_id) and module not in ignore_module:
                        _flmt_c.start_cd(event.group_id)
                        await bot.send_group_msg(
                            group_id=event.group_id, message="此功能正在维护"
                        )
                except ActionFailed:
                    pass
                raise IgnoredException("此功能正在维护")
    # 其他封禁检测(BanInfo)
    user_id = event.user_id
    group_id = event.group_id if hasattr(event, "group_id") else None
    if group_id and await BanInfo.is_plugin_ban(module, user_id, group_id):
        raise IgnoredException("用户于群内被禁用此插件中")  # 针对使用cd、count提示进行刷屏的封禁处理
    if await BanInfo.is_plugin_ban(module, user_id, None):
        await send_ban_reply(bot, matcher, event, user_id, None, module)
        raise IgnoredException("用户于全群被禁用此插件中")  # 针对master自主封禁用户使用插件权限
    if await BanInfo.is_super_ban(user_id):
        raise IgnoredException("用户处于超级黑名单中")  # 针对master自主封禁用户
    if await BanInfo.is_ban(user_id, None):
        await send_ban_reply(bot, matcher, event, user_id, None, None)
        raise IgnoredException("用户处于黑名单中")  # 针对master自主封禁用户
    # 以下为限制检测 #######################################################
    # 以下为限制检测 #######################################################
    # 以下为限制检测 #######################################################
    # 以下为限制检测 #######################################################
    # 以下为限制检测 #######################################################
    # 以下为限制检测 #######################################################
    # Count(plugins2count_manager, BanInfo)
    if plugins2count_manager.check_plugin_count_status(module):
        plugin_count_data = plugins2count_manager.get_plugin_count_data(module)
        rst = plugin_count_data["rst"]
        count_type_ = event.user_id
        if plugin_count_data["limit_type"] == "group" and isinstance(event, GroupMessageEvent):
            count_type_ = event.group_id
        # 使用次数耗尽
        if not plugins2count_manager.check(module, count_type_):
            plugins2count_manager.add_count_ban(module, event.user_id)
            if rst:
                if plugins2count_manager.get_count_ban(module, event.user_id)\
                        >= plugins2count_manager.get_count_ban_maxcount(module) - 1:
                    if not plugins2count_manager.check_count_ban(module, event.user_id):
                        await send_msg("明明告诉过你不能再用了...今日内将不再受理你使用此功能的指令。[at]", bot, event)
                        remain_time = int(time.mktime(
                            (datetime.datetime.today()+datetime.timedelta(hours=24)).date().timetuple()
                        ) - time.time())
                        await BanInfo.ban_plugin(module, 9, remain_time, event.user_id, event.group_id)
                        plugins2count_manager.remove_count_ban(module, event.user_id)
                    else:
                        await send_msg("你已达该功能今日使用上限，不可以再使用了噢！(￣へ￣[at]", bot, event)
                else:
                    if "[count]" in rst:
                        count = plugins2count_manager.get_count(module)
                        rst = rst.replace("[count]", str(count))
                    rst = await init_rst(rst, event)
                    await send_msg(rst, bot, event)
            else:
                if not plugins2count_manager.check_count_ban(module, event.user_id):
                    await send_msg("防刷屏检测，今日内将不再受理你使用此功能的指令。[at]", bot, event)
                    remain_time = int(time.mktime(
                        (datetime.datetime.today() + datetime.timedelta(hours=24)).date().timetuple()
                    ) - time.time())
                    await BanInfo.ban_plugin(module, 9, remain_time, event.user_id, event.group_id)
                    plugins2count_manager.remove_count_ban(module, event.user_id)
            raise IgnoredException(f"{module} count次数限制...")
        # 仍有使用次数
        else:
            count_flag = True if module not in oppose_count_modules else False
            plugins2count_manager.set_flag(module, event, count_flag)
            plugins2count_manager.remove_count_ban(module, event.user_id)
    # Cd(plugins2cd_manager,BanInfo)
    if plugins2cd_manager.check_plugin_cd_status(module):
        plugin_cd_data = plugins2cd_manager.get_plugin_cd_data(module)
        rst = plugin_cd_data["rst"]
        if (
            plugins2cd_manager.get_plugin_data(module).get("check_type") == "all"
            or (isinstance(event, GroupMessageEvent) and plugin_cd_data["check_type"] == "group")
            or (isinstance(event, PrivateMessageEvent) and plugin_cd_data["check_type"] == "private")
        ):
            cd_type_ = event.user_id
            if plugin_cd_data["limit_type"] == "group" and isinstance(event, GroupMessageEvent):
                cd_type_ = event.group_id
            # cd没好
            if not plugins2cd_manager.check(module, cd_type_):
                # 功能cd限制拉黑预警次数加一
                plugins2cd_manager.add_cd_ban(module, event.user_id)
                if rst:
                    if plugins2cd_manager.get_cd_ban_count(module, event.user_id)\
                            >= plugins2cd_manager.get_cd_ban_maxcount(module) - 1:
                        if not plugins2cd_manager.check_cd_ban(module, event.user_id):
                            await send_msg("防刷屏检测，1小时内你被禁止使用此功能。[at]", bot, event)
                            await BanInfo.ban_plugin(module, 9, 3600, event.user_id, event.group_id)
                            plugins2cd_manager.remove_cd_ban(module, event.user_id)
                        # 最后通牒(
                        else:
                            cd = plugins2cd_manager.get_cd(module, cd_type_)
                            await send_msg(f"功能还在cd中啦，再无视咱就不理你了！[剩余cd:{cd}s][at]", bot, event)
                    else:
                        # 触发正常cd回复
                        if "[cd]" in rst:
                            cd = plugins2cd_manager.get_cd(module, cd_type_)
                            rst = rst.replace("[cd]", str(cd))
                        rst = await init_rst(rst, event)
                        await send_msg(rst, bot, event)
                else:
                    if not plugins2cd_manager.check_cd_ban(module,event.user_id):
                        await send_msg("防刷屏检测，1小时内你被禁止使用此功能。[at]", bot, event)
                        await BanInfo.ban_plugin(module, 9, 3600, event.user_id, event.group_id)
                        plugins2cd_manager.remove_cd_ban(module, event.user_id)
                raise IgnoredException(f"{module} 正在cd中...")
            # cd好了
            else:
                cd_flag = True if module not in oppose_cd_modules else False
                plugins2cd_manager.set_flag(module, event, cd_flag)
                plugins2cd_manager.remove_cd_ban(module, event.user_id)
    # Block(plugins2block_manager)
    if plugins2block_manager.check_plugin_block_status(module):
        plugin_block_data = plugins2block_manager.get_plugin_block_data(module)
        rst = plugin_block_data["rst"]
        if (
            plugin_block_data["check_type"] == "all"
            or (isinstance(event, GroupMessageEvent) and plugin_block_data["check_type"] == "group")
            or (isinstance(event, PrivateMessageEvent) and plugin_block_data["check_type"] == "private")
        ):
            block_type_ = event.user_id
            if plugin_block_data["limit_type"] == "group" and isinstance(event, GroupMessageEvent):
                block_type_ = event.group_id
            # 插件仍在阻塞(30秒)
            if plugins2block_manager.check(block_type_, module):
                if rst:
                    rst = await init_rst(rst, event)
                    await send_msg(rst, bot, event)
                raise IgnoredException(f"{event.user_id}正在调用{module}....")
            # 插件阻塞完毕,开启新一轮阻塞(30秒)
            else:
                plugins2block_manager.set_true(block_type_, module)


@run_postprocessor
async def _(matcher: Matcher, bot: Bot, event: Event):
    # 非消息、戳一戳活动跳过
    if isinstance(event, MessageEvent) or isinstance(event, PokeNotifyEvent):
        module = matcher.plugin_name
        # 解除插件阻塞
        # Block
        if plugins2block_manager.check_plugin_block_status(module)\
            and str(event.user_id) not in bot.config.superusers:
            plugin_block_data = plugins2block_manager.get_plugin_block_data(module)
            check_type = plugin_block_data["check_type"]
            limit_type = plugin_block_data["limit_type"]
            if (
                (isinstance(event, PrivateMessageEvent) and check_type == "private")
                or (isinstance(event, GroupMessageEvent) and check_type == "group")
                or check_type == "all"
            ):
                if limit_type == "group" and hasattr(event, "group_id"):
                    block_type_ = event.group_id
                else:
                    block_type_ = event.user_id
                plugins2block_manager.set_false(block_type_, module)
        # 判断是否增加使用次数
        # Count
        if (
            plugins2count_manager.check_plugin_count_status(module)
            and str(event.user_id) not in bot.config.superusers
        ):
            plugin_count_data = plugins2count_manager.get_plugin_count_data(module)
            limit_type = plugin_count_data["limit_type"]
            count_type_ = event.user_id
            if limit_type == "group" and hasattr(event, "group_id"):
                count_type_ = event.group_id
            flag, num = plugins2count_manager.get_flag(module, event)
            if flag:
                plugins2count_manager.increase(module, count_type_, num)
        # 判断是否让插件进入CD
        # CD
        if (
            plugins2cd_manager.check_plugin_cd_status(module)
            and str(event.user_id) not in bot.config.superusers
        ):
            plugin_cd_data = plugins2cd_manager.get_plugin_cd_data(module)
            check_type = plugin_cd_data["check_type"]
            limit_type = plugin_cd_data["limit_type"]
            if (
                (isinstance(event, PrivateMessageEvent) and check_type == "private")
                or (isinstance(event, GroupMessageEvent) and check_type == "group")
                or plugins2cd_manager.get_plugin_data(module).get("check_type") == "all"
            ):
                cd_type_ = event.user_id
                if limit_type == "group" and hasattr(event, "group_id"):
                    cd_type_ = event.group_id
                flag, num = plugins2cd_manager.get_flag(module, event)
                if flag:
                    plugins2cd_manager.start_cd(module, cd_type_, cd_count=num)


async def send_ban_reply(
        bot: Bot,
        matcher: Matcher,
        event: Union[MessageEvent, PokeNotifyEvent],
        user_id: int,
        group_id: int = None,
        module: str = None
):
    cd_tag = f'{user_id}_{group_id}_{module}'
    if _flmt_b.check(cd_tag) and matcher.priority != 100:
        ban_result = "你暂时不能使用此功能，" if module else "你还在小黑屋内，"
        if matcher.plugin_name not in ignore_module:
            _flmt_b.start_cd(cd_tag)
            try:
                if module:
                    time = await BanInfo.check_plugin_ban_time(module, user_id, group_id)
                else:
                    time = await BanInfo.check_ban_time(user_id, group_id)
                if is_number(time):
                    time = timeremain(float(time))
                    reply = at(user_id) + ban_result + f"预计{time}后解禁"
                elif time == "∞":
                    if module:
                        reply = at(user_id) + "你被禁止使用此功能"
                    else:
                        return
                else:
                    time = str(time) + "分钟"
                    reply = at(user_id) + ban_result + f"预计{time}后解禁"
                if hasattr(event, "group_id"):
                    await bot.send_group_msg(group_id=event.group_id, message=reply)
                else:
                    await bot.send_private_msg(user_id=event.user_id, message=reply)
            except ActionFailed:
                pass