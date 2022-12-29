from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent
from configs.config import NICKNAME
from models.level_user import LevelUser
from utils.utils import is_number, timeremain
from models.ban_info import BanInfo
from services.log import logger
from typing import Union


def parse_ban_time(msg: str) -> Union[int, str]:
    """
    解析ban时长
    :param msg: 文本消息
    """
    if not msg:
        return -1
    msg = msg.split()
    if len(msg) == 1:
        if not is_number(msg[0].strip()):
            return "参数必须是数字！"
        return int(msg[0]) * 60 * 60
    else:
        if not is_number(msg[0].strip()) or not is_number(msg[1].strip()):
            return "参数必须是数字！"
        return int(msg[0]) * 60 * 60 + int(msg[1]) * 60


async def a_ban(qq: int, time: int, user_name: str, event: MessageEvent, ban_level: int = None) -> str:
    """
    群组拉黑
    :param qq: qq
    :param time: ban时长，-1为永久
    :param user_name: ban用户昵称
    :param event: event
    :param ban_level: ban级别，9为超管封禁
    """
    if isinstance(event, GroupMessageEvent):
        ban_level = await LevelUser.get_user_level(event.user_id, event.group_id)
    if await BanInfo.ban(ban_level, time, qq, event.group_id):
        logger.info(
            f"USER {event.user_id} GROUP {event.group_id} 将 USER {qq} 封禁 时长 {time / 60} 分钟"
        )
        result = f"已经将 {user_name} 加入{NICKNAME}的黑名单了！"
        if time != -1:
            result += f"将在 {timeremain(time)} 后解封"
        else:
            result += f"将在 ∞ 分钟后解封"
    else:
        time = float(await BanInfo.check_ban_time(qq))
        result = f"{user_name} 已在黑名单！预计 {timeremain(time)}后解封"
    return result










