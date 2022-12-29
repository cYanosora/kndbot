from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import MessageEvent
from ._model import WordBank


async def check(event: MessageEvent, state: T_State) -> bool:
    # 先检测群内是否有设置词条，没有就不匹配了，省事
    if hasattr(event, 'group_id') and not await WordBank.exist_any_problem(event.group_id):
        return False
    # 将用户发言转化为可匹配的格式化问句
    problem = await WordBank.message2problem(event.message)
    # print('从message转化为problem:', problem)
    # 检测问句是否有对应答句
    if problem and (await WordBank.check(event, problem) is not None):
        state["problem"] = problem
        return True
    else:
        return False

