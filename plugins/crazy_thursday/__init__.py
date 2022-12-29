from random import choice
import os
from pathlib import Path
from re import match
import nonebot
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, GROUP, MessageEvent
try:
    import ujson as json
except ModuleNotFoundError:
    import json

global_config = nonebot.get_driver().config
if not hasattr(global_config, 'crazy_path'):
    CRAZY_PATH = os.path.join(os.path.dirname(__file__), 'resource')
else:
    CRAZY_PATH = global_config.crazy_path

__plugin_name__ = "疯狂星期四"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = f'''
usage:
    KFC疯狂星期四
    指令:
    [疯狂星期X] 随机输出KFC疯狂星期四文案
    [狂乱X曜日] 随机输出KFC疯狂星期四文案
'''.strip()
__plugin_settings__ = {
    "cmd": ["疯狂星期四", "狂乱木曜日"],
}
__plugin_cd_limit__ = {
    "cd": 8,
    "limit_type": "group",
    "rst": "别搁这狂乱x曜日了，让我歇[cd]秒..."
}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再继续呢[at]",
}
crazy = on_regex(r'^疯狂星期\S$', permission=GROUP, priority=5, block=True)
crazy_jp = on_regex(r'^狂乱\S曜日$', permission=GROUP, priority=5, block=True)

def rndKfc(msg, jp = False):
    day = (match(r'狂乱(\S)曜日', msg) if jp else match(r'疯狂星期(\S)', msg.replace('天', '日'))).group(1)
    tb = ['月', '一', '火', '二', '水', '三', '木', '四', '金', '五', '土', '六', '日', '日']
    if day not in tb:
        return 
    idx = int(tb.index(day)/2)*2
    # json数据存放路径
    path = Path(CRAZY_PATH) / 'post.json'
    # 将json对象加载到数组
    with open(path, 'r', encoding='utf-8') as f:
        kfc = json.load(f).get('post')
    # 随机选取数组中的一个对象
    return choice(kfc).replace('星期四', '星期' + tb[idx+1]).replace('周四', '周' + tb[idx+1]).replace('木曜日', tb[idx] + '曜日')

@crazy.handle()
async def _(bot: Bot, event: MessageEvent):
    reply = rndKfc(event.get_plaintext())
    if reply:
        await crazy.finish(reply, at_sender=True)

@crazy_jp.handle()
async def _(bot: Bot, event: MessageEvent):
    reply = rndKfc(event.get_plaintext(), True)
    if reply:
        await crazy_jp.finish(reply, at_sender=True)
