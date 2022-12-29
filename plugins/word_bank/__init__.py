from manager import Config
import nonebot

Config.add_plugin_config(
    "word_bank",
    "WORD_BANK_LEVEL [LEVEL]",
    6,
    name="词库问答",
    help_="设置增删词库的权限等级",
    default_value=6
)

nonebot.load_plugins("plugins/word_bank")
