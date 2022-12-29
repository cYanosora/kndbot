from nonebot import on_command
from nonebot.params import CommandArg
from services.log import logger
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message, GROUP
from nonebot.typing import T_State
from .data_source import translate_msg


__plugin_name__ = "翻译"
__plugin_type__ = "实用工具"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    会生草的翻译机你喜欢吗？
    指令：
        英翻 [英文]
        翻英 [中文]
        日翻 [日文]
        翻日 [中文]
        韩翻 [韩文]
        翻韩 [中文]
""".strip()
__plugin_settings__ = {
    "cmd": ["翻译"],
}
__plugin_cd_limit__ = {"cd": 5, "rst": "别急，[cd]s后再用！[at]",}

translate = on_command(
    "translate",
    aliases={"英翻", "英文翻译", "翻英", "翻译英文", "日翻", "日文翻译", "翻日", "翻译日文", "韩翻", "韩文翻译", "翻韩", "翻译韩文"},
    permission=GROUP,
    priority=5,
    block=True
)


@translate.handle()
async def _(state: T_State, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg:
        state["msg"] = msg


@translate.got("msg", prompt="你要翻译的消息是啥？")
async def _(event: MessageEvent, state: T_State):
    msg = state["msg"]
    if len(msg) > 150:
        await translate.finish("翻译过长！请不要超过150字", at_sender=True)
    await translate.send(await translate_msg(state["_prefix"]["raw_command"], msg))
    logger.info(
        f"(USER {event.user_id}, GROUP "
        f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) 使用翻译：{msg}"
    )
