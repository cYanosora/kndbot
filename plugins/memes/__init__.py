from io import BytesIO
from typing import Union
from nonebot.params import Depends
from nonebot.matcher import Matcher
from nonebot.typing import T_Handler
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import MessageSegment, GROUP, MessageEvent
from utils.limit_utils import ignore_count
from .depends import regex
from .data_source import memes
from .utils import Meme, help_image

__plugin_name__ = "表情包制作"
__plugin_type__ = "图片类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage
    生成各种生草表情包
    请发送 查看表情包列表 获取支持的表情包指令
    举例：
        喜报 bot风控了
        鲁迅说 我没说过这句话
        王境泽 我就是饿死 死外边 不会吃你们一点东西 真香
    注意：
        每段文本用空格隔开
""".strip()
__plugin_settings__ = {
    "cmd": ["表情包制作", "表情包列表"],
}
__plugin_cd_limit__ = {"cd": 10, "rst": "别急，[cd]s后再用！",}
__plugin_block_limit__ = {"rst": "表情包还在生成中...别急！"}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再继续呢[at]",
}

help_cmd = on_command(
    "查看表情包列表",
    aliases={"查看表情包", "表情包列表", "表情包制作", "表情包制作列表", "查看表情包制作列表"},
    block=True,
    permission=GROUP,
    priority=5
)


@help_cmd.handle()
async def _():
    img = await help_image(memes)
    if img:
        await help_cmd.finish(MessageSegment.image(img))


def create_matchers():
    def handler(meme: Meme) -> T_Handler:
        async def handle(
            matcher: Matcher, event: MessageEvent, res: Union[str, BytesIO] = Depends(meme.func)
        ):
            matcher.stop_propagation()
            if isinstance(res, str):
                ignore_count(matcher.plugin_name, event)
                await matcher.finish(res)
            await matcher.finish(MessageSegment.image(res))

        return handle

    for meme in memes:
        on_message(
            regex(meme.pattern),
            block=False,
            priority=5,
        ).append_handler(handler(meme))


create_matchers()
