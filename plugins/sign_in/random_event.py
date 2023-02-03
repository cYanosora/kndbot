from manager import Config
import random


PROB_DATA = None


def random_event(impression: float) -> 'Union[str, int], str':
    """
    签到随机事件
    :param impression: 好感度
    :return: 额外奖励 和 类型
    """
    global PROB_DATA
    if not PROB_DATA:
        PROB_DATA = {
            Config.get_config("sign_in", "SIGN_CARD3_PROB"): '好感双倍卡3',
            Config.get_config("sign_in", "SIGN_CARD2_PROB"): '好感双倍卡2',
            Config.get_config("sign_in", "SIGN_CARD1_PROB"): '好感双倍卡1',
            Config.get_config("sign_in", "RESIGN_CARD_PROB"): '补签卡'
        }
    rand = random.random() - impression / 1000
    for prob in PROB_DATA.keys():
        if rand <= prob:
            return PROB_DATA[prob], 'props'
    gold = random.randint(1, random.randint(1, int(1 if impression < 1 else impression)))
    max_sign_gold = Config.get_config("sign_in", "MAX_SIGN_GOLD")
    gold = max_sign_gold if gold > max_sign_gold else gold
    return gold, 'gold'
