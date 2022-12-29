from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, GROUP
from nonebot.params import CommandArg
from .data import text_to_emoji

__plugin_name__ = "语句抽象化"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
        语句抽象化/抽象化/抽象 [要抽象的语句]
""".strip()
__plugin_settings__ = {
    "cmd": ["语句抽象化", "抽象"],
}
__plugin_cd_limit__ = {"cd": 5, "rst": "别急，[cd]s后再用！[at]",}
__plugin_block_limit__ = {}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再继续呢[at]",
}

abstract = on_command("语句抽象化", aliases={"抽象", "抽象化"}, permission=GROUP, priority=5, block=True)


@abstract.handle()
async def _(arg: Message = CommandArg()):
    if arg.extract_plain_text().strip():
        target_text = arg.extract_plain_text().strip()
        abstract_responses = text_to_emoji(target_text)
        if abstract_responses:
            await abstract.send(abstract_responses)
        else:
            await abstract.send("抽象失败，可能是结果太抽象的问题！")
