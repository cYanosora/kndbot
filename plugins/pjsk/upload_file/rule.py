from nonebot.adapters.onebot.v11 import Event, NoticeEvent
from nonebot.typing import T_RuleChecker


def rule() -> T_RuleChecker:
    async def check_rule(event: Event) -> bool:
        print('rule:',event)
        if isinstance(event, NoticeEvent) and event.notice_type == 'offline_file':
            return True
        return False
    return check_rule