import asyncio
from typing import Tuple, Any
from nonebot import on_regex, get_driver, Driver
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import RegexGroup
from nonebot.rule import to_me
from configs.config import BOT_URL
from configs.path_config import DATA_PATH
from models.level_user import LevelUser
from services import logger
from utils.message_builder import image
from .data_source import create_help_img, get_plugin_help
import os

driver: Driver = get_driver()

__plugin_name__ = "帮助 [Hidden]"
__plugin_version__ = 0.1


group_help_path = DATA_PATH / "group_help"
group_help_path.mkdir(exist_ok=True, parents=True)
for x in os.listdir(group_help_path):
    group_help_image_path = group_help_path / x
    group_help_image_path.unlink()

simple_help = on_regex("(.*)(?:怎么用|帮助|help)$", rule=to_me(), priority=3, block=True)


@simple_help.handle()
async def _(bot: Bot, event: MessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    # 群聊触发
    if hasattr(event, 'group_id'):
        msg = reg_group[0].strip()
        _type = 0
        # 单个功能帮助
        if msg:
            if await LevelUser.get_user_level(event.user_id, event.group_id) > 0:
                _type = 1
            if str(event.user_id) in bot.config.superusers:
                _type = 2
            res = get_plugin_help(msg, _type)
            if res:
                await simple_help.finish(image(b64=res))
            else:
                await simple_help.finish("没有此功能的帮助信息...")
        # 功能大全帮助
        else:
            _image_path = group_help_path / f"{event.group_id}.png"
            if not _image_path.exists():
                await create_help_img(event.group_id, _image_path)
            await simple_help.send(
                f"帮助文档👉https://{BOT_URL}/docs\n"+image(_image_path)
            )
    # 私聊触发
    else:
        await simple_help.finish(f"帮助文档👉https://{BOT_URL}/docs")


# 每个bot启动时生成bot所在的每个群的帮助图片
@driver.on_bot_connect
async def _(bot: Bot):
    group_list = []
    gl = [g["group_id"] for g in await bot.get_group_list()]
    for g in gl:    # [int]
        if g not in group_list:
            group_list.append(g)
            _image_path = group_help_path / f"{g}.png"
            if not _image_path.exists():
                await create_help_img(g, _image_path)
                logger.info(f'生成群组({g})的简易帮助图片')
                await asyncio.sleep(5)
