from io import BytesIO
from typing import Union
from nonebot.params import Depends
from nonebot.matcher import Matcher
from nonebot.typing import T_Handler
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import MessageSegment, GROUP, MessageEvent
from utils.limit_utils import access_count, access_cd
from .data_source import commands
from .depends import split_msg, regex
from .utils import Command, help_image, help_pic_image

__plugin_name__ = "头像表情包/图片操作"
__plugin_type__ = "图片类"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    触发方式：指令 + @任何人/qq号/自己/图片
    使用 "@任何人/qq号/自己" 将以目标qq的头像作为图片，也可以手动自带图片
    请发送 "头像表情包" "改图指令" 查看所有支持的指令

    大部分指令可以不需要文字，但必须有图片，其中一些可以携带参数的指令如下：
        摸 ?圆 [图片]                             : 不带参数"圆"时，默认图片为正方形
        对称 ?[上/下/左/右] [图片]          : 不带位置参数时，默认以"左边"对称
        典中典 [文字] [图片]                   : 必须自带文案
        我朋友?[昵称]说 *[文字] [图片]   : 文字可有多段，使用"空格"分开
        
        可以携带多张图片的指令:
            我永远喜欢、远离
            
        带文字时会使用指定文案的指令:
            万能表情、玩游戏、采访、阿尼亚喜欢、安全感、看图标、看扁、不文明、一起
            
        带文字时会使用指定文字作为昵称的指令:
            小天使、兑换券、问问、交个朋友、关注
    示例：
        结婚申请 @任何人
        膜 qq号
        垃圾桶 自己
        出警 [图片] ?[图片]
        改图水平翻转 [图片]
        图片旋转 90 [图片]    :图片逆时针旋转90°
""".strip()
__plugin_settings__ = {
    'cmd': ["头像表情包", "图片操作", "改图指令", "改图"]
}
__plugin_cd_limit__ = {"cd": 10, "rst": "别急，[cd]s后再用！",}
__plugin_count_limit__ = {
    "max_count": 20,
    "limit_type": "user",
    "rst": "今天已经玩够了吧，还请明天再继续呢[at]",
}

help_cmd = on_command("头像表情包", aliases={"图片操作指令", "改图指令"}, permission=GROUP, block=True, priority=5)


@help_cmd.handle()
async def _(event: MessageEvent):
    if event.get_plaintext().strip() in ["图片操作指令", "改图指令"]:
        img = await help_pic_image()
    else:
        img = await help_image(commands[1:])
    if img:
        await help_cmd.finish(MessageSegment.image(img))


def create_matchers():
    def handler(command: Command) -> T_Handler:
        async def handle(
            matcher: Matcher, event: MessageEvent, res: Union[str, BytesIO] = Depends(command.func)
        ):
            if isinstance(res, str):
                await matcher.finish(res)
            else:
                access_count(matcher.plugin_name, event)
                access_cd(matcher.plugin_name, event)
                await matcher.finish(MessageSegment.image(res))

        return handle

    for command in commands:
        on_message(
            regex(command.pattern, command.arg_type),
            block=True,
            priority=5,
        ).append_handler(handler(command), parameterless=[split_msg()])


create_matchers()
