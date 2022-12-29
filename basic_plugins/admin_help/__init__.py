from nonebot import on_command
from nonebot.adapters.onebot.v11 import GROUP
from utils.message_builder import image
from .data_source import create_help_image, admin_help_image


__plugin_name__ = '管理帮助 [Admin]'
__plugin_version__ = 0.1
__plugin_settings__ = {
    "admin_level": 1,
}

admin_help = on_command(
    "管理员帮助",
    aliases={"群管帮助", "管理帮助"},
    permission=GROUP,
    priority=1,
    block=True
)

if admin_help_image.exists():
    admin_help_image.unlink()


@admin_help.handle()
async def _():
    if not admin_help_image.exists():
        await create_help_image()
    await admin_help.send(image('admin_help_img.png'))
