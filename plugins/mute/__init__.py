import re
from typing import Tuple
from nonebot import on_message, on_command
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.matcher import Matcher
from nonebot.message import run_postprocessor
from nonebot.params import Command, CommandArg
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    ActionFailed,
    Message,
    Event,
    PokeNotifyEvent
)
from utils.utils import scheduler
from configs.config import NICKNAME
from manager import Config
from models.ban_info import BanInfo
from .rule import check
from services import logger
from manager import admin_manager, mute_manager, mute_data_manager
from utils.utils import is_number
from utils.message_builder import at

__plugin_name__ = "刷屏禁言/拉黑 [Admin]"
__plugin_type__ = "群相关"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
admin_usage：
    刷屏禁言相关操作，需要 {NICKNAME} 有群管理员权限
    无权限时仅能使用 "限制触发指令频率" 的刷屏拉黑功能
    
    指令：
        设置刷屏禁言参数 [X] [T] [N] [M]    : 一次性设置完所有参数
        设置刷屏检测类型 [X]                : 见注意事项, 默认为限制复读频率
        设置刷屏检测时间 [T]                : 见注意事项, 默认为60秒
        设置刷屏检测次数 [N]                : 见注意事项, 默认为3次
        设置刷屏禁言时长 [M]                : 见注意事项, 默认为0分钟(关闭状态)
        查看刷屏禁言参数                    : 查看当前的刷屏检测设置
    效果：
        T 秒内满足刷屏条件 N 次，禁言 M 分钟
    注意：
        X的取值有3种：0,1,2
        * X=0代表限制复读频率(规定时间内仅记入 '用户同一句话' 的发送次数)
        * X=1代表限制群员发言频率(规定时间内计入 '用户任何发言' 的发送次数)
        * X=2代表限制触发指令频率(规定时间内计入 '用户任何触发bot指令' 的次数)
        T的取值范围限制为1~120(秒)
        N的取值范围限制为2~30(次数)
        M的取值范围限制为0~43200(分钟)(0为关闭)
    举例：
        设置刷屏禁言参数 0 60 3 1       :群内有人一分钟重复发送同一消息3次，禁言拉黑1分钟
        设置刷屏禁言参数 1 5 3 1        :群内有人5秒发消息3次，禁言拉黑1分钟
        设置刷屏禁言参数 2 30 3 1       :群内有人30秒触发3次bot的指令，禁言拉黑1分钟
""".strip()
__plugin_configs__ = {
    "MUTE_LEVEL [LEVEL]": {"value": 6, "help": "更改禁言设置的管理权限", "default_value": 6},
    "MUTE_DEFAULT_COUNT": {"value": 3, "help": "刷屏禁言默认检测次数", "default_value": 3},
    "MUTE_DEFAULT_TIME": {"value": 60, "help": "刷屏检测默认规定时间", "default_value": 60},
    "MUTE_DEFAULT_DURATION": {"value": 0, "help": "刷屏检测默认禁言时长（分钟）","default_value": 0},
    "MUTE_DEFAULT_TYPE": {"value": 'mute', "help": "刷屏检测默认禁言类型（mute/allmute/cmdmute）","default_value": 'mute'},
}
__plugin_settings__ = {
    "admin_level": Config.get_config("mute", "MUTE_LEVEL"),
    "cmd": ["刷屏禁言"]
}

ignore_modules = [
    "help", "admin_help", "super_help", "custom_welcome_message",
    "switch_rule", "update_group_member", 
    "invite_manager", "my_info", "dialogue", "update_info",
    "admin_config", "ban", "broadcast", "dialogue", "group_handle",
]

mute = on_message(priority=1, permission=GROUP, rule=check, block=False)
mute_setting = on_command(
    "设置刷屏禁言参数",
    aliases={"设置刷屏检测类型", "设置刷屏检测时间", "设置刷屏检测次数", "设置刷屏禁言时长", "查看刷屏禁言参数"},
    permission=GROUP,
    block=True,
    priority=5
)


def messagePreprocess(message: str) -> str:
    contained_images = {}
    images = re.findall(r'\[CQ:image.*?]', message)
    for i in images:
        contained_images.update({i: re.findall(r'\[.*file=(.*?),.*]', i)[0]})
    for i in contained_images:
        message = message.replace(i, f'[{contained_images[i]}]')
    return message


@mute.handle()
async def _(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
    group_id = str(event.group_id)
    # 无禁言配置采用默认群禁言检测配置
    mute_data = mute_data_manager.get_group_mute_settings(group_id)
    # 获取用户发送的群聊消息
    add_key = f'{event.group_id}_{event.user_id}'
    add_msg = messagePreprocess(event.raw_message)
    mute_manager.append(
        add_key, add_msg, mute_data['time'], mute_data['type']
    )
    # 若不可以继续发言
    if not mute_manager.check_count(add_key, mute_data['count']):
        mute_manager.clear(add_key)
        try:
            self_info = await bot.get_group_member_info(group_id=event.group_id, user_id=int(bot.self_id))
            flag = True if self_info["role"] in ["owner", "admin"] else False
            user_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
            flag = flag and True if user_info["role"] == "member" else False
        except:
            flag = False
        # 只有bot是群管时才会对基础禁言类型作处理
        if flag:
            try:
                await bot.set_group_ban(
                    group_id=event.group_id,
                    user_id=event.user_id,
                    duration=int(mute_data["duration"] * 60),
                )
            except ActionFailed:
                # 如果用户尚未被ban，提示用户被ban
                if not await BanInfo.is_ban(user_id=event.user_id):
                    await mute.send(
                        f"检测到恶意刷屏，{NICKNAME}要把你禁言/拉黑咯，{mute_data['duration']}分钟后见",
                        at_sender=True
                    )
                    matcher.stop_propagation()
            else:
                await mute.send(
                    f"检测到恶意刷屏，{NICKNAME}要把你禁言/拉黑咯，{mute_data['duration']}分钟后见",
                    at_sender=True
                )
                matcher.stop_propagation()
            await BanInfo.ban(5, int(60 * mute_data['duration']), event.user_id, event.group_id)
            logger.warning(
                f"USER {event.user_id} GROUP {event.group_id} "
                f'检测刷屏 被禁言/拉黑 {mute_data["duration"]} 分钟'
            )
            matcher.stop_propagation()


@run_postprocessor
async def _(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    if not hasattr(event, 'group_id'):
        return
    if not (isinstance(event, GroupMessageEvent) or isinstance(event, PokeNotifyEvent)):
        return 
    group_id = str(event.group_id)
    user_id = event.get_user_id()
    # 无禁言配置采用默认群禁言检测配置
    mute_data = mute_data_manager.get_group_mute_settings(group_id)
    if (
        mute_data['duration'] == 0 or
        mute_data['type'] != 'cmdmute' or
        str(event.get_user_id()) in bot.config.superusers or
        matcher.plugin_name in admin_manager.keys() or
        matcher.priority in [1, 2, 100] or
        matcher.plugin_name in ignore_modules
    ):
        return
    add_key = f'{group_id}_{user_id}'
    add_msg = matcher.plugin_name
    # 根据插件返回状态决定是否增加发言次数
    callback_flag = mute_manager.append(
        add_key, add_msg, mute_data['time'], mute_data['type']
    )
    if callback_flag:
        # 若增加发言次数后，指令调用达到刷屏阈值，禁言
        if not mute_manager.check_count(add_key, mute_data['count']):
            mute_manager.clear(add_key)
            try:
                self_info = await bot.get_group_member_info(group_id=event.group_id, user_id=int(bot.self_id))
                # 检测bot自身是否是群管理员，不是则无需尝试撤回群员消息
                flag = True if self_info["role"] in ["owner", "admin"] else False
                # 检测对方是否是成员，不是则无需尝试撤回
                user_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
                flag = flag and True if user_info["role"] == "member" else False
            except:
                flag = False
            bantype = "禁言/拉黑" if flag else "拉黑"
            try:
                if flag:
                    await bot.set_group_ban(
                        group_id=int(group_id),
                        user_id=int(user_id),
                        duration=int(mute_data["duration"] * 60),
                    )
            except ActionFailed:
                pass
            await BanInfo.ban(5, int(60 * mute_data['duration']), int(user_id), int(group_id))
            await bot.send_group_msg(
                group_id=int(group_id),
                message=at(int(user_id)) +
                f"检测到恶意刷屏，{NICKNAME}要把你{bantype}咯，{mute_data['duration']}分钟后见",
            )
            matcher.stop_propagation()
            logger.warning(
                f"USER {user_id} GROUP {group_id} "
                f'检测刷屏 被{bantype} {mute_data["duration"]} 分钟'
            )


@mute_setting.handle()
async def _(event: GroupMessageEvent, cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()):
    dic_type2type = {
        '0': 'mute',
        '1': 'allmute',
        '2': 'cmdmute',
    }
    dic_type2text = {
        '0': '限制复读频率', 'mute': '限制复读频率',
        '1': '限制发言频率', 'allmute': '限制发言频率',
        '2': '限制触发指令频率', 'cmdmute': '限制触发指令频率'
    }
    group_id = str(event.group_id)
    mute_data = mute_data_manager.get_group_mute_settings(group_id)
    msg = arg.extract_plain_text().strip()
    if cmd[0] == "查看刷屏禁言参数":
        await mute_setting.finish(
            f'检测类型：{dic_type2text[mute_data["type"]]}\n'
            f'最大次数：{mute_data["count"]} 次\n'
            f'规定时间：{mute_data["time"]} 秒\n'
            f'禁言时长：{mute_data["duration"]} 分钟\n'
            f"* 在规定时间内发送符合刷屏条件的消息到达最大次数则禁言\n当禁言时长为0时关闭此功能 *"
        )
    if cmd[0] == "设置刷屏禁言参数":
        if len(msg.split()) < 4:
            await mute_setting.finish("请提供完整参数！指令：设置刷屏禁言参数 [检测类型:0/1/2] [检测时间/秒] [检测次数] [禁言时长/分钟]", at_sender=True)
        m0, m1, m2, m3 = msg.split()[:4]
        m0 = dic_type2type.get(m0)
        if m0 and is_number(m1) and is_number(m2) and is_number(m3):
            if not(
                0 < int(m1) <= 120 and
                1 < int(m2) <= 30 and
                0 <= int(m3) <= 43200
            ):
                await mute_setting.finish('请提供正确范围内的参数！', at_sender=True)
            mute_data_manager.set_group_mute_settings(
                group_id,
                **{
                    "type": m0,
                    "time": int(m1),
                    "count": int(m2),
                    "duration": int(m3)
                }
            )
            m0 = dic_type2text[m0]
            await mute_setting.send(
                f'刷屏检测：\n' +
                f'设置刷屏检测类型为 {m0}\n' +
                f'设置刷屏检测时间为 {m1} 秒\n' +
                f'设置刷屏检测次数为 {m2} 次\n' +
                f'设置刷屏禁言时长为 {m3} 分钟\n'
            )
            logger.info(
                f'USER {event.user_id} GROUP {group_id} {cmd}：{msg}'
            )
        else:
            await mute_setting.finish("请提供正确参数！指令：设置刷屏检测配置 [检测类型:0/1/2] [检测时间/秒] [检测次数] [禁言时长/分钟]")
    else:
        if cmd[0] == "设置刷屏检测类型":
            msg = dic_type2type.get(msg)
            if not msg:
                await mute_setting.finish("设置的类型必须是0、1、2中的一种(具体含义见对应功能帮助)", at_sender=True)
            mute_data_manager.set_group_mute_settings(
                group_id,
                **{"type": msg}
            )
            msg = dic_type2text.get(msg)
        elif cmd[0] == "设置刷屏检测时间":
            if not (0 < int(msg) <= 120):
                await mute_setting.finish("设置的时间范围必须是1~120(单位:秒)！", at_sender=True)
            mute_data_manager.set_group_mute_settings(
                group_id,
                **{"time": int(msg)}
            )
            msg += "秒"
        elif cmd[0] == "设置刷屏检测次数":
            if not (1 < int(msg) <= 30):
                await mute_setting.finish("设置的次数范围必须是2~30次！", at_sender=True)
            mute_data_manager.set_group_mute_settings(
                group_id,
                **{"count": int(msg)}
            )
            msg += " 次"
        elif cmd[0] == "设置刷屏禁言时长":
            if not (0 <= int(msg) <= 43200):
                await mute_setting.finish("设置的禁言时长范围必须是0~43200分钟(30天)！(0代表关闭)", at_sender=True)
            mute_data_manager.set_group_mute_settings(
                group_id,
                **{"duration": int(msg)}
            )
            msg += " 分钟"
        await mute_setting.send(f'刷屏检测：{cmd[0]}为 {msg}')
        logger.info(
            f'USER {event.user_id} GROUP {group_id} {cmd[0]}：{msg}'
        )


# 定时清除超时禁言数据
@scheduler.scheduled_job(
    "interval",
    minutes=1,
    seconds=30
)
async def _():
    mute_manager.clear_data()
    logger.info(f"[定时任务]:清除超时禁言数据")
