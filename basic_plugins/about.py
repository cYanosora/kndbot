from nonebot import on_command
from nonebot.rule import to_me
from configs.config import NICKNAME
from utils.message_builder import image


__plugin_name__ = f"关于{NICKNAME}"
__plugin_usage__ = f"""
usage：
    关于{NICKNAME}
    指令：
        关于{NICKNAME}        ： 获取{NICKNAME}bot的一些介绍，有很多字
""".strip()
__plugin_type__ = '其他'
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": [f"关于{NICKNAME}", "关于", "关于奏宝"],
}


update_info1 = on_command(f"关于{NICKNAME}", aliases={'关于奏宝', "关于knd"}, priority=5, block=True)
update_info2 = on_command(f"关于", rule=to_me(), priority=5, block=True)


@update_info1.handle()
async def _():
    await update_info1.finish(image("other/bot_info.png"))


@update_info2.handle()
async def _():
    await update_info2.finish(image("other/bot_info.png"))
