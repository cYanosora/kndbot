from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent, GROUP
from nonebot import on_command, on_message, on_regex
from nonebot.params import RegexGroup
from nonebot.rule import to_me
from nonebot.typing import T_State
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from ._data_source import (
    change_group_switch,
    set_plugin_status,
    get_plugin_status,
    group_current_status,
    set_group_bot_status
)
from services.log import logger
from configs.config import NICKNAME
from manager import Config
from utils.utils import is_number
from nonebot.permission import SUPERUSER
from typing import Tuple, Any
from .rule import switch_rule


up_cmd = Config.get_config("admin_bot_manage", "WAKEUP_BOT_CMD", ['起来工作', '唤醒'])
down_cmd = Config.get_config("admin_bot_manage", "SHUTDOWN_BOT_CMD", ['去休息吧', '休眠'])

__plugin_name__ = "群功能开关 [Admin]"
__plugin_type__ = "群相关"
__plugin_version__ = 0.1
__plugin_admin_usage__ = f"""
admin_usage：
    群内功能与被动技能开关
    指令：
        开启/关闭[功能]               :通用插件开关
        群被动状态                    :查看群被动状态
        开启/关闭全部被动              :群被动总开关
        @bot {'/'.join(up_cmd)}     :让{NICKNAME}工作
        @bot {'/'.join(down_cmd)}   :让{NICKNAME}睡大觉
""".strip()
__plugin_superuser_usage__ = """
usage:
    功能总开关与指定群禁用，私聊中master使用
    指令：
        功能状态
        开启/关闭[功能] [*群号]                          :指定群某功能开关
        开启/关闭[功能] [p或private、g或group、a或all]   :指定私聊/群聊/所有情况某功能开关
""".strip()
__plugin_settings__ = {
    "admin_level": Config.get_config("admin_bot_manage", "CHANGE_GROUP_SWITCH_LEVEL"),
    "cmd": ["群功能开关", "开启功能", "关闭功能", "功能开关"]
}

switch_rule_matcher = on_message(rule=switch_rule, permission=GROUP | SUPERUSER, priority=3, block=True)

plugins_status = on_command("功能状态", permission=SUPERUSER, priority=1, block=True)

group_task_status = on_command("群被动状态", permission=GROUP | SUPERUSER, priority=3, block=True)

group_status = on_regex(
    f"^({'|'.join(up_cmd+down_cmd)})$",
    permission=SUPERUSER | GROUP,
    rule=to_me(),
    priority=3,
    block=True
)


@switch_rule_matcher.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    _cmd = state["cmd"]
    # 群聊开关
    if isinstance(event, GroupMessageEvent):
        await switch_rule_matcher.send(await change_group_switch(_cmd, event.group_id))
        logger.info(f"USER {event.user_id} GROUP {event.group_id} 使用群功能管理命令 {_cmd}")
    # 超管私聊
    elif str(event.user_id) in bot.config.superusers:
        block_type = state.get("block_type")
        block_type = block_type if block_type else "a"
        type_dic = {
            "all": "all", "private": "private", "group": "group",
            "a": "all", "p": "private", "g": "group"
        }
        # 超管指定某些群某功能开关状态
        gl = [int(i) for i in block_type.split() if is_number(i)]
        if gl:
            group_list = []
            all_group = [
                g["group_id"] for g in await bot.get_group_list()
            ]
            for g in gl:
                if g in all_group:
                    group_list.append(g)
            if not group_list:
                await switch_rule_matcher.finish(f"请提供{NICKNAME}已加入的群聊号")
            text = f"已{_cmd[:2]}以下群聊的 {_cmd[2:].strip()} 功能：\n"
            for g in group_list:
                await change_group_switch(_cmd, g, True)
                group_name = (await bot.get_group_info(group_id=g))["group_name"]
                text += f"{group_name}({g})\n"
            await switch_rule_matcher.finish(image(pic2b64(text2image(text))))
        # 超管指定私聊/群聊/全部某功能开关状态
        elif block_type in type_dic.keys():
            block_type = type_dic[block_type]
            await set_plugin_status(bot, _cmd, block_type)
            if block_type == "group":
                await switch_rule_matcher.send(f"已在群聊中{_cmd[:2]}功能：{_cmd[2:].strip()}")
            elif block_type == "private":
                await switch_rule_matcher.send(f"已在私聊中{_cmd[:2]}功能：{_cmd[2:].strip()}")
            else:
                await switch_rule_matcher.send(f"已{_cmd[:2]}功能：{_cmd[2:].strip()}")
        else:
            await switch_rule_matcher.finish("格式错误：开启/关闭[功能] [群号]或[p/g/a]")
        logger.info(f"USER {event.user_id} 使用功能管理命令 {_cmd} | {block_type}")


@plugins_status.handle()
async def _():
    await plugins_status.send(await get_plugin_status())


@group_task_status.handle()
async def _(event: GroupMessageEvent):
    await group_task_status.send(await group_current_status(event.group_id))


@group_status.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    cmd = reg_group[0]
    if cmd in down_cmd:
        msg = set_group_bot_status(event.group_id, False)
    else:
        msg = set_group_bot_status(event.group_id, True)
    await group_status.send(msg)
    logger.info(f"USER {event.user_id} GROUP {event.group_id} 使用总开关命令：{cmd}")
