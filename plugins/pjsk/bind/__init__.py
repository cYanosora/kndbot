import re
import time
from typing import Tuple
from nonebot import on_command
from nonebot.params import CommandArg, Command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from .._config import BUG_ERROR, NOT_BIND_ERROR, REFUSED_ERROR, ID_ERROR
from .._utils import verifyid, get_userid_preprocess
from .._models import PjskBind
try:
    import ujson as json
except:
    import json

__plugin_name__ = "绑定账号"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    pjsk绑定账号，私聊可用
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    指令：
        绑定/bind [id]           绑定烧烤id
        解绑/unbind              解绑烧烤id
        给看/不给看               公开/隐藏自己的烧烤信息(默认为公开)
        查时间                   查询烧烤账号创建时间
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["bind", "绑定账号", "烧烤相关", "uni移植"],
}


# pjsk绑定
pjsk_bind = on_command('bind', aliases={"绑定"}, priority=5, block=True)

# pjsk解绑
pjsk_unbind = on_command('unbind', aliases={"解绑"}, priority=5, block=True)

#pjsk给看
pjsk_look = on_command('给看', aliases={"不给看"}, priority=5, block=True)

#pjsk查时间
pjsk_ctime = on_command('查时间', priority=5, block=True)


@pjsk_bind.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    arg = re.sub(r'\D', "", msg.extract_plain_text().strip())
    if not arg:
        await pjsk_bind.finish("绑定成...？你id呢？", at_sender=True)
    if arg.isdigit() and verifyid(arg):
        await PjskBind.add_bind(event.user_id, int(arg))
        await pjsk_bind.finish(f"绑定成功", at_sender=True)
    else:
        await pjsk_bind.finish(ID_ERROR, at_sender=True)


@pjsk_unbind.handle()
async def _(event: MessageEvent):
    flag = await PjskBind.del_bind(event.user_id)
    if flag:
        await pjsk_unbind.finish(f"解绑成功", at_sender=True)
    else:
        await pjsk_unbind.finish("解绑成...？你还没绑定过呢", at_sender=True)


@pjsk_look.handle()
async def _(event: MessageEvent, cmd: Tuple[str, ...] = Command()):
    isprivate = False if cmd[0][:2] == '给看' else True
    if not await PjskBind.check_exists(event.user_id, 0):
        await pjsk_bind.finish(NOT_BIND_ERROR)
    if await PjskBind.set_look(event.user_id, isprivate, 0):
        await pjsk_bind.finish(f"{'不给看！' if isprivate else '给看！'}")
    else:
        await pjsk_bind.finish(BUG_ERROR)


@pjsk_ctime.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    state = await get_userid_preprocess(event, msg)
    if reply := state['error']:
        await pjsk_ctime.finish(reply, at_sender=True)
    userid = state['userid']
    isprivate = state['private']
    if isprivate:
        await pjsk_ctime.finish(REFUSED_ERROR)
    passtime = userid / 1000 / 1024 / 4096
    await pjsk_ctime.finish(
        time.strftime(
            '注册时间：%Y-%m-%d %H:%M:%S',
            time.localtime(1600218000 + int(passtime))
        )
    )
