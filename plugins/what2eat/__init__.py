import nonebot
from configs.path_config import DATA_PATH
from manager import Config

Config.add_plugin_config(
    "what2eat",
    "SUPERUSERS",
    [],
    help_="超级用户",
    default_value=[],
)
Config.add_plugin_config(
    "what2eat",
    "WHAT2EAT_PATH",
    str(DATA_PATH.absolute() / "what2eat"),
    help_="资源路径",
    default_value=str(DATA_PATH.absolute() / "what2eat"),
)
Config.add_plugin_config(
    "what2eat",
    "EATING_LIMIT",
    10,
    help_="每个餐点询问bot吃什么的上限次数",
    default_value=10
)
Config.add_plugin_config(
    "what2eat",
    "GROUP_ID",
    [],
    help_="记录每个群组的id，便于设置群特色菜单",
    default_value=[]
)

nonebot.load_plugins("plugins/what2eat")
