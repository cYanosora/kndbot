from nonebot import on_command
from nonebot.permission import SUPERUSER
from configs.path_config import TEMP_PATH
from utils.utils import scheduler
from services.log import logger
from manager import resources_manager
import asyncio
import time
import os

__plugin_name__ = "清理临时数据 [Superuser]"
__plugin_type__ = "数据管理"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    清理临时数据
    指令：
        清理临时数据
""".strip()
__plugin_settings = {
    "cmd": ["清理临时数据"]
}


clear_data = on_command(
    "清理临时数据", permission=SUPERUSER, priority=1, block=True
)


resources_manager.add_temp_dir(TEMP_PATH)


@clear_data.handle()
async def _():
    await clear_data.send("开始清理临时数据....")
    size = await asyncio.get_event_loop().run_in_executor(None, _clear_data)
    await clear_data.send("共清理了 {:.2f}MB 的数据...".format(size / 1024 / 1024))


def _clear_data() -> float:
    size = 0
    for dir_ in resources_manager.get_temp_data_dir():
        if dir_.exists():
            for file in os.listdir(dir_):
                file = dir_ / file
                if file.is_file():
                    try:
                        if time.time() - os.path.getatime(file) > 300:
                            file_size = os.path.getsize(file)
                            file.unlink()
                            size += file_size
                    except Exception as e:
                        logger.error(f"清理临时数据错误...{type(e)}：{e}")
    return float(size)


@scheduler.scheduled_job(
    "cron",
    hour=1,
    minute=1,
)
async def _():
    size = await asyncio.get_event_loop().run_in_executor(None, _clear_data)
    logger.info("自动清理临时数据完成，" + "共清理了 {:.2f}MB 的数据...".format(size / 1024 / 1024))
