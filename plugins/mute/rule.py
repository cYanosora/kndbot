from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot

from manager import mute_data_manager


def check(bot: Bot, event: GroupMessageEvent) -> bool:
    group_id = str(event.group_id)
    # 无禁言配置采用默认群禁言检测配置
    mute_data = mute_data_manager.get_group_mute_settings(group_id)
    # 没有禁言配置不用禁言 或者是 bot指令型禁言交给hook处理 或者是 超管
    if(
        mute_data['duration'] == 0 or
        mute_data['type'] == 'cmdmute' or
        str(event.user_id) in bot.config.superusers
    ):
        return False
    return True