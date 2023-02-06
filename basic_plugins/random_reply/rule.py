import time
from nonebot.adapters.onebot.v11 import GroupMessageEvent, PokeNotifyEvent
from nonebot.params import Command
from nonebot.typing import T_RuleChecker, T_State
from services import logger
from .models import retry_manager, UserInfo


# 不需要用户消息的规则
def normal_rule(command: Command) -> T_RuleChecker:
    async def check_args(
            event: GroupMessageEvent, state: T_State
    ) -> bool:
        if (not command.need_at) or (command.need_at and event.is_tome()):
            user = UserInfo(qq=event.user_id, group=event.group_id)
            state["users"] = user
            return True
        else:
            return False

    return check_args


# 需要用户消息的规则
def check_rule(command: Command) -> T_RuleChecker:
    async def check_args(
            event: GroupMessageEvent, state: T_State
    ) -> bool:
        if event.reply:
            return False
        if (not command.need_at) or (command.need_at and event.is_tome()):
            msg = event.get_plaintext()
            user = UserInfo(qq=event.user_id, group=event.group_id, text=msg)
            if not user:
                return False
            state["users"] = user
            return True
        else:
            return False

    return check_args


# 戳一戳的特殊规则
def poke_rule(command: Command) -> T_RuleChecker:
    async def check_args(
            event: PokeNotifyEvent, state: T_State
    ) -> bool:
        if (not command.need_at) or (command.need_at and event.is_tome()):
            try:
                if event.group_id is None:
                    return False
            except Exception as e:
                logger.warning(f"戳一戳报错: {e}")
                return False
            if event.self_id == event.target_id:
                user = UserInfo(qq=event.user_id, group=event.group_id)
                state["users"] = user
                return True
        else:
            return False

    return check_args


# 多轮对话触发规则
def retry_rule() -> T_RuleChecker:
    async def check_args(event: GroupMessageEvent) -> bool:
        retry_info = retry_manager.get(event.user_id, event.group_id)
        if retry_info:
            if retry_info["time"] + 30 < time.time():
                retry_manager.remove(event.user_id, event.group_id)
                return False
            return True
        return False
    return check_args