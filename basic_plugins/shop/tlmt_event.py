from nonebot.adapters.onebot.v11 import Message, Bot
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from configs.path_config import DATA_PATH, IMAGE_PATH
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
try:
    import ujson as json
except:
    import json
import nonebot
nonebot.require("shop_scheduler")
from .shop_scheduler import gift_data as _gift_data
gift_data = _gift_data

__plugin_name__ = "限时活动"
__plugin_type__ = '其他'
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    为奏宝生日准备的限时活动的功能说明书
    指令：
        限时活动            ：获得限时活动的具体介绍图
        查询礼物资格         ：查询自己当前是否有资格获得礼物道具
    注意：
        生日礼物道具务必在奏宝生日当天使用，仅生日礼物2可以兑换纪念品道具
        纪念品道具在商店内展示，目前无法售出
        使用方式：
        生日礼物1 指令：使用生日礼物1
        生日礼物2 指令：使用生日礼物2兑换[纪念品道具名] 使用例： 使用生日礼物2兑换康乃馨
""".strip()
__plugin_settings__ = {
    "cmd": ["限时活动"],
}


limit_event = on_command("限时活动", priority=5, block=True, permission=GROUP)
my_qual = on_command(
    "查询礼物资格", aliases={"我的礼物资格", "我的礼物", "我的资格"},
    priority=5, block=True, permission=GROUP | SUPERUSER
)


@limit_event.handle()
async def _():
    await limit_event.finish(image(IMAGE_PATH / 'limit_event.jpg'))


@my_qual.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msgs = arg.extract_plain_text().strip().split()
    if msgs and str(event.user_id) in bot.config.superusers and all(i.isdigit() for i in msgs):
        qq = int(msgs[0])
        group = int(msgs[1])
    else:
        qq = event.user_id
        group = event.group_id
    reply = get_qual(qq, group)
    await my_qual.finish(reply, at_sender=True)

lik2level = {
    160: '5',
    100: '4',
    55: '3',
    25: '2',
    10: '1',
    0: '0'
}


def get_level(impr: float) -> str:
    for i in lik2level:
        if impr >= i:
            return lik2level[i]
    return '0'


def get_qual(qq: int, group: int):
    global gift_data
    if not gift_data:
        with open(DATA_PATH / 'limit_event.json', 'r', encoding='utf-8') as f:
            gift_data = json.load(f)
    qq = str(qq)
    group = str(group)
    text = '获取信息失败，也许你2月9日之前从来没有签过到，若提示有误请联系master'
    if group in gift_data.keys():
        groupinfo = gift_data[group]
        total_days = groupinfo['days']
        total_count = len(groupinfo['users'])
        for userinfo in groupinfo['users']:
            if userinfo['qq'] == qq:
                signdays = userinfo['signdays']
                rank = userinfo['rank']
                gift = userinfo['gift']
                impr = userinfo['impr']
                level = get_level(impr)
                rankrate = rank / total_count * 100
                signrate = signdays / total_days * 100
                text  = f'截止2月9日，小奏已经加群{total_days}天\n'\
                        f'你已签到{signdays}天，漏签率{100-signrate:.2f}%\n' \
                        f'好感度{impr:.2f}(等级:{level})\n' \
                        f'在群内已签到用户中天数排第{rank}名(前{rankrate:.2f}%)\n'\
                        f'你可以获得的礼物为:{gift}'
                break
    return image(b64=pic2b64(text2image(text)))
