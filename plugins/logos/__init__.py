import shlex
from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.typing import T_Handler
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import MessageSegment, Message
from .data_source import create_logo, commands

__plugin_name__ = "logo制作"
__plugin_type__ = "图片类"
__plugin_version__ = 0.1
__plugin_usage__ = '''
usage:
    5000兆等风格logo生成
    若原始文本中要带空格，请用英文引号包围文本
    举例：
        五千兆/5kcy    5000兆円　欲しい
        youtube       油管
        google        谷歌
        douyin        抖音        
        phlogo        Pron Hub
'''.strip()
__plugin_settings__ = {
    "cmd": ["logo", "各类logo"],
}
__plugin_count_limit__ = {
    "max_count": 30,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再继续呢[at]",
}


async def handle(matcher: Matcher, style: str, text: str):
    arg_num = commands[style]['arg_num']
    texts = [text] if arg_num == 1 else shlex.split(text)
    if len(texts) != arg_num:
        await matcher.finish('参数数量不符')

    image = await create_logo(style, texts)
    if image:
        await matcher.finish(MessageSegment.image(image))
    else:
        await matcher.finish('出错了，请稍后再试')


def create_matchers():
    def create_handler(style: str) -> T_Handler:
        async def handler(msg: Message = CommandArg()):
            text = msg.extract_plain_text().strip()
            if not text:
                await matcher.finish()
            await handle(matcher, style, text)

        return handler

    for style, params in commands.items():
        matcher = on_command(style, aliases=params['aliases'],
                             priority=5, block=True)
        matcher.append_handler(create_handler(style))

create_matchers()
