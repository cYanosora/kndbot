from nonebot import on_command
from nonebot.permission import SUPERUSER
from configs.path_config import IMAGE_PATH
from utils.message_builder import image
from .data_source import create_help_image


__plugin_name__ = '超级用户帮助 [Superuser]'
__plugin_version__ = 0.1

superuser_help_image = IMAGE_PATH / 'superuser_help.png'

if superuser_help_image.exists():
    superuser_help_image.unlink()

super_help = on_command(
    "超级用户帮助", aliases={"超管帮助"}, priority=1, permission=SUPERUSER, block=True
)


@super_help.handle()
async def _():
    if not superuser_help_image.exists():
        await create_help_image()
    await super_help.finish(image(superuser_help_image))
