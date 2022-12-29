from nonebot.typing import T_RuleChecker
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent,
    GroupDecreaseNoticeEvent,
    NoticeEvent,
    GroupBanNoticeEvent,
)


def group_in_rule() -> T_RuleChecker:
    async def check(event: NoticeEvent) -> bool:
        if isinstance(event, GroupIncreaseNoticeEvent):
            return True
        else:
            return False
    return check


def group_de_rule() -> T_RuleChecker:
    async def check(event: NoticeEvent) -> bool:
        if isinstance(event, GroupDecreaseNoticeEvent):
            return True
        else:
            return False
    return check


def group_ban_rule() -> T_RuleChecker:
    async def check(event: NoticeEvent) -> bool:
        if isinstance(event, GroupBanNoticeEvent) and event.is_tome():
            return True
        else:
            return False
    return check

