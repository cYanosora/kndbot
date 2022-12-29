import re
from nonebot.adapters.onebot.v11 import Event, PrivateMessageEvent, GroupAdminNoticeEvent
from nonebot.typing import T_State, T_RuleChecker
from manager import group_manager, plugins2settings_manager
from utils.utils import get_message_text, is_number
from services.log import logger

cmd = []


def switch_rule(event: Event, state: T_State) -> bool:
    """
    检测文本是否是功能命令开关
    :param event: pass
    :param state: pass
    """
    global cmd
    try:
        # 初始化命令开关
        if not cmd:
            cmd = ["全部被动", "全部功能"]
            # 加载群被动插件
            _data = group_manager.get_task_data()
            for key in _data:
                cmd.append(_data[key])
            # 加载一般插件
            _data = plugins2settings_manager.get_data()
            for key in _data:
                try:
                    if isinstance(_data[key]["cmd"], list):
                        for x in _data[key]["cmd"]:
                            cmd.append(x)
                    else:
                        cmd.append(key)
                except KeyError:
                    pass

        msg = get_message_text(event.json()).strip()
        # 若为超管在私聊中使用功能开关
        if isinstance(event, PrivateMessageEvent):
            block_type = msg.split()[-1]
            if is_number(block_type) or block_type in ["all", "private", "group", "a", "p", "g"]:
                state["block_type"] = block_type
                msg = " ".join(msg.split()[:-1])
        if res := re.search(r'^(?:开启|关闭) *(.+)', msg):
            if res.group(1).strip() in cmd:
                state["cmd"] = msg[:2] + msg[2:].strip()
                return True
        return False
    except Exception as e:
        logger.error(f"检测是否为功能开关命令发生错误 {type(e)}: {e}")
    return False


def admin_notice_rule() -> T_RuleChecker:
    async def check(event: Event) -> bool:
        if isinstance(event, GroupAdminNoticeEvent):
            return True
        return False
    return check

