from typing import Tuple

from nonebot import on_command
from nonebot.params import CommandArg, Command
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
        翻译           [文本]         ：默认翻译为中文
        
        翻英/英翻       [文本]         ：翻译为英文
        翻译英文/英文翻译 [文本]         ：翻译为英文
        
        翻日/日翻       [文本]         ：翻译为日文
        翻译日文/日文翻译 [文本]         ：翻译为日文
        
        翻韩/韩翻       [文本]         ：翻译为韩文
        翻译韩文/韩文翻译 [文本]         ：翻译为韩文
        
        翻法/法翻       [文本]         ：翻译为法文
        翻译法文/法文翻译 [文本]         ：翻译为法文
        
        翻德/德翻       [文本]         ：翻译为德文
        翻译德文/德文翻译 [文本]         ：翻译为德文
        
        翻俄/俄翻       [文本]         ：翻译为俄文
        翻译俄文/俄文翻译 [文本]         ：翻译为俄文
""".strip()
__plugin_settings__ = {
    "cmd": ["翻译"],
}
__plugin_cd_limit__ = {"cd": 5, "rst": "别急，[cd]s后再用！[at]",}

translate = on_command(
    "翻译",
    aliases={
        "英翻", "英文翻译", "翻英", "翻译英文",
        "日翻", "日文翻译", "翻日", "翻译日文",
        "韩翻", "韩文翻译", "翻韩", "翻译韩文",
        "法翻", "法文翻译", "翻法", "翻译法文",
        "德翻", "德文翻译", "翻德", "翻译德文",
        "俄翻", "俄文翻译", "翻俄", "翻译俄文",
    },
    permission=GROUP,
    priority=5,
    block=True
)


@translate.handle()
async def _(state: T_State, cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()):
    state['translate_cmd'] = cmd[0]
    msg = arg.extract_plain_text().strip()
    if msg:
        state["translate_msg"] = msg


@translate.got("translate_msg", prompt="你要翻译的消息是啥？")
async def _(event: MessageEvent, state: T_State):
    msg = state["translate_msg"]
    if len(msg) > 150:
        await translate.finish("翻译过长！请不要超过150字", at_sender=True)
    await translate.send(await translate_msg(state["translate_cmd"], msg))
    logger.info(
        f"(USER {event.user_id}, GROUP "
        f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'}) 使用翻译：{msg}"
    )
