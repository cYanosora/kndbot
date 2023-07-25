import nonebot
from typing import Dict, Any
from nonebot.adapters.onebot.v11 import Bot, ActionFailed
from utils.utils import FreqLimiter, CountLimiter

# 风控提醒cd
_fk_fqlmt = FreqLimiter(3600, 3)  # 1h内3次消息发送失败则视为可能风控
_fk_warn_clmt = CountLimiter(1)


# 风控提醒
@Bot.on_called_api
async def handle_api_call(bot: Bot, exception, api: str, data: Dict[str, Any], result):
    if exception is not None and isinstance(exception, ActionFailed):
        bot_qq = bot.self_id
        # 未满足风控检测条件时
        if _fk_fqlmt.count_check(bot_qq):
            # 准备提醒
            _fk_warn_clmt.clear(bot_qq)
            _fk_fqlmt.start_cd(bot_qq)
        # 满足风控检测条件时(1小时3次)
        else:
            # 如果尚未被提醒过(风控期间只提醒一次，设置不风控时恢复次数)
            if _fk_warn_clmt.get_count(bot_qq) == 0:
                super_qq = list(bot.config.superusers)[0]
                msg = f"奏宝bot({bot_qq})疑似被风控，请及时解除"
                try:
                    await bot.send_private_msg(user_id=int(super_qq), message=msg)
                    _fk_warn_clmt.add(bot_qq)
                # 风控到私聊都发不出去, 尝试用另一只bot提醒
                except ActionFailed:
                    bots = list(nonebot.get_bots().values())
                    for each in bots:
                        if each.self_id == bot_qq:
                            continue
                        else:
                            bot = each
                            break
                    await bot.send_private_msg(user_id=int(super_qq), message=msg)
                    _fk_warn_clmt.add(bot_qq)
                except:
                    pass

# bot掉线通知
driver = nonebot.get_driver()
@driver.on_bot_disconnect
async def bot_disconnect(bot: Bot):
    bot_qq = bot.self_id
    bots = list(nonebot.get_bots().values())
    super_qq = list(bot.config.superusers)[0]
    msg = f"检测到奏宝bot({bot_qq})掉线，请及时处理"
    if 1 <= len(bots) <= 4:
        for each in bots:
            if each.self_id == bot_qq:
                continue
            else:
                bot = each
                await bot.send_private_msg(user_id=int(super_qq), message=msg)
                break
                