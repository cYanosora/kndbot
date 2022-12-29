from nonebot.adapters.onebot.v11 import (
    FriendRequestEvent,
    GroupRequestEvent,
    FriendAddNoticeEvent,
    Event
)
from nonebot.typing import T_RuleChecker


def friend_reply_rule() -> T_RuleChecker:
    async def check(event: Event) -> bool:
        if isinstance(event, FriendAddNoticeEvent):
            return True
        return False
    return check


def group_request_rule() -> T_RuleChecker:
    async def check(event: Event) -> bool:
        if isinstance(event, GroupRequestEvent):
            return True
        return False
    return check


def friend_request_rule() -> T_RuleChecker:
    async def check(event: Event) -> bool:
        if isinstance(event, FriendRequestEvent):
            return True
        return False
    return check
