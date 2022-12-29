from manager import Config
import nonebot


Config.add_plugin_config(
    "admin_bot_manage:custom_welcome_message",
    "SET_GROUP_WELCOME_MESSAGE_LEVEL [LEVEL]",
    5,
    name="群管理员操作",
    help_="设置群欢迎消息权限",
    default_value=5,
)

Config.add_plugin_config(
    "admin_bot_manage:switch_rule",
    "CHANGE_GROUP_SWITCH_LEVEL [LEVEL]",
    5,
    help_="开关群功能权限",
    default_value=5,
)

Config.add_plugin_config(
    "admin_bot_manage",
    "ADMIN_DEFAULT_AUTH",
    5,
    help_="默认群管理员权限",
    default_value=5
)
Config.add_plugin_config(
    "admin_bot_manage",
    "WAKEUP_BOT_CMD",
    ['起来工作', '唤醒'],
    help_="bot群开机指令",
    default_value=['起来工作', '唤醒']
)
Config.add_plugin_config(
    "admin_bot_manage",
    "SHUTDOWN_BOT_CMD",
    ['去休息吧', '休眠'],
    help_="bot群停机指令",
    default_value=['去休息吧', '休眠']
)
nonebot.load_plugins("basic_plugins/admin_bot_manage")
