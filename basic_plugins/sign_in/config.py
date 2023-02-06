from configs.path_config import IMAGE_PATH

SIGN_RESOURCE_PATH = IMAGE_PATH / 'sign' / 'sign_res'
SIGN_TODAY_CARD_PATH = IMAGE_PATH / 'sign' / 'today_card'
SIGN_BORDER_PATH = SIGN_RESOURCE_PATH / 'border'
SIGN_BACKGROUND_PATH = SIGN_RESOURCE_PATH / 'background'

SIGN_BORDER_PATH.mkdir(exist_ok=True, parents=True)
SIGN_BACKGROUND_PATH.mkdir(exist_ok=True, parents=True)


lik2relation = {
    '0': '路人',
    '1': '陌生',
    '2': '初识',
    '3': '一般',
    '4': '熟悉',
    '5': '信赖',
    # '6': '厚谊',
    # '7': '亲密'
}

level2attitude = {
    '0': '马马虎虎',
    '1': '可以交流',
    '2': '感觉不坏',
    '3': '逐渐习惯',
    '4': '保持友谊',
    '5': '交情甚笃',
    # '6': '坦诚相见',
    # '7': '像杯面一样'
}

weekdays = {
    1: 'Mon',
    2: 'Tue',
    3: 'Wed',
    4: 'Thu',
    5: 'Fri',
    6: 'Sat',
    7: 'Sun'
}

lik2level = {
    # 325: '7',
    # 235: '6',
    160: '5',
    100: '4',
    55: '3',
    25: '2',
    10: '1',
    0: '0'
}






