import nonebot
from nonebot.adapters.onebot.v11 import Adapter
from services.db_context import init, disconnect

nonebot.init()
driver = nonebot.get_driver()
driver.register_adapter(Adapter)
config = driver.config
driver.on_startup(init)
driver.on_shutdown(disconnect)
nonebot.load_plugin("nonebot_plugin_htmlrender")
nonebot.load_plugin("nonebot_plugin_apscheduler")
nonebot.load_plugins("basic_plugins")
nonebot.load_plugins("plugins")
nonebot.load_plugins("basic_plugins/hooks")


if __name__ == "__main__":
    nonebot.run()
