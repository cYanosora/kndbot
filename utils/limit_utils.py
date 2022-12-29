from nonebot.adapters.onebot.v11 import MessageEvent
from manager import plugins2cd_manager, plugins2count_manager, mute_manager


# 插件内根据实际情况决定无需进入cd
def ignore_cd(module: str, event: MessageEvent):
    """
    : param module: 模块名称
    : param event: 事件
    """
    plugins2cd_manager.set_flag(module, event, False)


# 插件内根据实际情况决定需要进入cd
def access_cd(module: str, event: MessageEvent, num: int = 1):
    """
    : param module: 模块名称
    : param event: 事件
    : param num: cd范围内已使用的次数
    """
    plugins2cd_manager.set_flag(module, event, True, num)


# 插件内根据实际情况自行调用，决定需要消耗使用次数
def access_count(module: str, event: MessageEvent, num: int = 1):
    """
    : param module: 模块名称
    : param event: 事件
    : param num: 消耗的使用次数
    """
    plugins2count_manager.set_flag(module, event, True, num)


# 插件内根据实际情况自行调用，决定无需消耗使用次数
def ignore_count(module: str, event: MessageEvent):
    """
    : param module: 模块名称
    : param event: 事件
    """
    plugins2count_manager.set_flag(module, event, False)


# 插件内根据实际情况自行调用，决定需要计入刷屏次数
def access_mute(key: str):
    """
    : param key: 群号_qq号
    """
    mute_manager.set_flag(key, True)


# 插件内根据实际情况自行调用，决定无需计入刷屏次数
def ignore_mute(key: str):
    """
    : param key: 群号_qq号
    """
    mute_manager.set_flag(key, False)
