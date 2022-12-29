from pathlib import Path
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent
from nonebot.log import logger
from nonebot.rule import to_me
from manager import Config
from models.group_member_info import GroupInfoUser
from utils.message_builder import image
from utils.utils import scheduler
from ._utils import eating_manager

__plugin_name__ = "今天吃什么"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    今天吃什么
    选择恐惧症？让Bot建议你今天吃什么！
    指令：
        今天吃什么    :问bot恰什么
        菜单         :查看群自定义菜单，管理菜单需要bot群管权限
    示例：
        奏宝，今天吃什么
        小奏，早上吃啥
        knd，夜宵造点啥
""".strip()
__plugin_settings__ = {
    "cmd": ["今天吃什么", "吃什么"],
}
__plugin_cd_limit__ = {"cd": 5, "rst": "唔..让我想[cd]秒后再来问我吧~[at]", }

what2eat = on_regex(
    r"^(今天|[早中午晚][上饭餐午]|早上|夜宵|宵夜|今晚)[吃造](什么|啥|点啥)",
    rule=to_me(),
    permission=GROUP,
    priority=5,
    block=True
)


@what2eat.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    msg, flag = eating_manager.get2eat(event)
    info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id)
    cardname = info.get("card", "") or info.get("nickname", "")
    nickname = await GroupInfoUser.get_group_member_nickname(event.user_id, event.group_id)
    user_name = nickname or cardname
    if user_name:
        msg = msg.replace('[user]', '你')
    else:
        msg = msg.replace('[user]', '你')
    img = image(Path(Config.get_config("what2eat", "WHAT2EAT_PATH") + "/feed.jpg"))
    if img and flag:
        msg += img
    await what2eat.finish(msg, at_sender=True)


# 重置吃什么次数，包括夜宵
@scheduler.scheduled_job("cron", hour="6,11,17,22", minute=0)
async def _():
    eating_manager.reset_eating()
    logger.info("今天吃什么次数已刷新")
