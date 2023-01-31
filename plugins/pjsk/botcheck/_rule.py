from nonebot.adapters.onebot.v11 import  GroupMessageEvent
from nonebot.typing import T_RuleChecker
from ._model import unibot


def check_rule() -> T_RuleChecker:
    async def check_args(event: GroupMessageEvent) -> bool:
        # print('rule:',unibot.starttime)
        if unibot.starttime > 0:
            return True
        return False
    return check_args