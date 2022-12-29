from nonebot.internal.matcher import Matcher
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import MessageSegment, GROUP, MessageEvent
from utils.limit_utils import access_cd, access_count
from .getdata import get_answer
from nonebot.log import logger
from datetime import datetime

__plugin_name__ = "青年大学习"
__plugin_type__ = "实用工具"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    青年大学习
    指令：
        青年大学习/大学习       : 获取最新一期的青年大学习答案
""".strip()
__plugin_settings__ = {
    "cmd": ["大学习", "青年大学习"],
}
__plugin_cd_limit__ = {"cd": 10, "rst": "别急，[cd]s后再用！[at]",}
__plugin_block_limit__ = {}
__plugin_count_limit__ = {
    "max_count": 3,
    "limit_type": "user",
    "rst": "你怎么看答案还要一天看好几次的，事不过三哦[at]",
}
college_study = on_command('青年大学习', aliases={'大学习'}, permission=GROUP, priority=5)


@college_study.handle()
async def _(matcher: Matcher, event: MessageEvent):
    try:
        await college_study.send("请耐心等候...正在获取答案中...")
        img = await get_answer()
        if img is None:
            await college_study.send("本周暂未更新青年大学习", at_sender=True)
        elif img == "未找到答案":
            await college_study.send("未找到答案", at_sender=True)
        elif img == "获取答案失败":
            await college_study.send("未获取到答案，疑似网页结构发生改变，解析失败", at_sender=True)
        else:
            access_cd(matcher.plugin_name, event)
            access_count(matcher.plugin_name, event)
            await college_study.send(MessageSegment.image(img), at_sender=True)
    except Exception as e:
        await college_study.send(f"出错了，请稍后再试呢", at_sender=True)
        logger.error(f"{datetime.now()}: 错误信息：{e}")
