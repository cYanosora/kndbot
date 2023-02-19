from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.typing import T_RuleChecker, T_State
from ._config import pjskguess, PJSK_GUESS, PJSK_ANSWER


def check_reply() -> T_RuleChecker:
    async def check_args(event: GroupMessageEvent, state: T_State) -> bool:
        if event.is_tome():
            for guess in pjskguess.keys():
                if (
                    event.group_id in pjskguess[guess] and
                    pjskguess[guess][event.group_id].get('isgoing', False)
                ):
                    state[PJSK_GUESS] = guess
                    if answer := event.raw_message.replace(f"[CQ:at,qq={event.self_id}]", "").strip():
                        state[PJSK_ANSWER] = answer.lower()
                        return True
        return False
    return check_args


def check_rule() -> T_RuleChecker:
    async def check_args(event: GroupMessageEvent, state: T_State) -> bool:
        for guess in pjskguess.keys():
            if (
                event.group_id in pjskguess[guess] and
                pjskguess[guess][event.group_id].get('isgoing', False)
            ):
                print('通过rule')
                state[PJSK_GUESS] = guess
                return True
        return False
    return check_args