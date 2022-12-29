import re
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GROUP, Message
from nonebot.params import CommandArg
from .._config import data_path
from .._utils import currentevent
from .._event_utils import drawevent
from .._models import EventInfo
from utils.message_builder import image

__plugin_name__ = "活动查询/event"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤活动信息，移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    限制每个群半分钟只能查询2次
    指令：
        event ?[活动id]                : 查看对应活动id的活动信息，无参数时默认为当前活动
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["event", "烧烤相关", "uni移植", "活动查询"],
}
__plugin_cd_limit__ = {"cd": 30, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# findevent
findevent = on_command('event', permission=GROUP, priority=5, block=True)


@findevent.handle()
async def _(arg: Message = CommandArg()):
    eventid = re.sub(r'\D', "", arg.extract_plain_text().strip())
    if not eventid:
        eventid = currentevent()['id']
    else:
        eventid = int(eventid)
    # 检查本地是否已经有活动图片
    path = data_path / 'eventinfo'
    path.mkdir(parents=True, exist_ok=True)
    save_path = path / f'event_{eventid}.png'
    if save_path.exists():
        await findevent.finish(image(save_path))
    else:
        eventinfo = EventInfo()
        if eventinfo.getevent(eventid):
            pic = await drawevent(eventinfo)
            pic.save(save_path)
            await findevent.finish(image(save_path))
        else:
            await findevent.finish("未找到活动或生成失败")
