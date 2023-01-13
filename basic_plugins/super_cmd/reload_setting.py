from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me

from models.group_info import GroupInfo
from manager import (
    plugins2cd_manager,
    plugins2settings_manager,
    plugins2block_manager,
    group_manager, plugins2count_manager,
)
from manager import Config
from services.log import logger
from utils.utils import scheduler, is_number

__plugin_name__ = "重载插件配置 [Superuser]"
__plugin_type__ = "数据管理"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    重载以下插件配置
    plugins2settings
    plugins2cd
    plugins2count
    plugins2block
    group_manager
    Config
    指令：
        重载配置 ?[all]      :带all参数，重置所有群聊默认功能开关
        重载配置 [群号]       :重置指定群聊默认功能开关
""".strip()
__plugin_settings = {
    "cmd": ["重载配置"]
}
__plugin_configs__ = {
    "AUTO_RELOAD": {
        "value": False,
        "help": "自动重载配置文件",
        "default_value": False
    },
    "AUTO_RELOAD_TIME": {
        "value": 180,
        "help": "控制自动重载配置文件时长",
        "default_value": 180
    }
}


reload_plugins_manager = on_command(
    "重载配置", rule=to_me(), permission=SUPERUSER, priority=1, block=True
)


@reload_plugins_manager.handle()
async def _(arg: Message = CommandArg()):
    arg = arg.extract_plain_text().strip()
    plugins2settings_manager.reload()
    plugins2cd_manager.reload()
    plugins2count_manager.reload()
    plugins2block_manager.reload()
    if arg:
        data = plugins2settings_manager.get_data()
        groups = await GroupInfo.get_all_group()
        if arg == 'all':
            for group in groups:
                for plugin in data.keys():
                    if not data[plugin]["default_status"]:
                        group_manager.block_plugin(plugin, int(group.group_id))
        elif is_number(arg):
            for group in groups:
                if arg == group.group_id:
                    for plugin in data.keys():
                        if not data[plugin]["default_status"]:
                            group_manager.block_plugin(plugin, int(group.group_id))
                    break
    group_manager.reload()
    Config.reload()
    await reload_plugins_manager.send("重载完成...")


@scheduler.scheduled_job(
    'interval',
    seconds=Config.get_config("reload_setting", "AUTO_RELOAD_TIME", 180),
)
async def _():
    if Config.get_config("reload_setting", "AUTO_RELOAD"):
        plugins2settings_manager.reload()
        plugins2cd_manager.reload()
        plugins2block_manager.reload()
        group_manager.reload()
        Config.reload()
        logger.debug("已自动重载所有配置文件...")
