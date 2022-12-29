from nonebot import on_regex
from configs.config import NICKNAME


__plugin_name__ = f"关于{NICKNAME}"
__plugin_type__ = "其他"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    想要更加了解小奏吗
    指令：
        关于{NICKNAME}
""".strip()
__plugin_settings__ = {
    "level": 1,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["关于"],
}


about = on_regex(f"^关于{NICKNAME}$", priority=5, block=True)


@about.handle()
async def _():
    msg = f"""
『一只可可爱爱的宵崎奏Bot』
简介: 基于绪山真寻Bot的开源项目二次开发的Bot，希望能被友好对待ヾ(@^▽^@)ノ
👇亲妈指路👇
项目地址：https://github.com/HibiKier/zhenxun_bot
文档地址：https://hibikier.github.io/zhenxun_bot/
""".strip()
    await about.send(msg)
