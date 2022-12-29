import shutil
import nonebot
from pathlib import Path
from asyncpg.exceptions import ConnectionDoesNotExistError, UndefinedColumnError
from utils.utils import scheduler, get_bot
from services.log import logger
from models.group_info import GroupInfo
from models.friend_user import FriendUser
from manager import Config
from ._data_source import update_member_info

Config.add_plugin_config(
    "_backup",
    "BACKUP_FLAG",
    True,
    help_="是否开启文件备份",
    default_value=True
)

Config.add_plugin_config(
    "_backup",
    "BACKUP_DIR_OR_FILE",
    ['data/configs', 'data/statistics', 'data/word_bank', 'data/manager', 'configs'],
    name="文件备份",
    help_="备份的文件夹或文件",
    default_value=[]
)

__plugin_name__ = "定时任务相关 [Hidden]"


# 每天定时更新所有群的群员信息
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=30,
)
async def _():
    bots = list(nonebot.get_bots().values())
    for bot in bots:
        gl = await bot.get_group_list()
        gl = [g["group_id"] for g in gl]
        for g in gl:
            try:
                await update_member_info(bot, g)
                logger.info(f"更新群组 g:{g} 成功")
            except Exception as e:
                logger.error(f"更新群组错误 g:{g} e:{e}")


# 快速更新未保存的群的群员信息
@scheduler.scheduled_job(
    "interval",
    minutes=5,
)
async def _():
    try:
        bots = list(nonebot.get_bots().values())
        for bot in bots:
            gl = await bot.get_group_list()
            gl = [g["group_id"] for g in gl]
            all_group = [x.group_id for x in await GroupInfo.get_all_group()]
            for g in gl:
                if g not in all_group:
                    await update_member_info(bot, g)
                    logger.info(f"快速更新未保存的群信息以及权限：{g}")
    except (IndexError, ConnectionDoesNotExistError, UndefinedColumnError):
        pass


# 每天定时更新所有群的群信息
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=1,
)
async def _():
    try:
        bot = get_bot()
        gl = await bot.get_group_list()
        gl = [g["group_id"] for g in gl]
        for g in gl:
            group_info = await bot.get_group_info(group_id=g)
            await GroupInfo.add_group_info(
                group_info["group_id"],
                group_info["group_name"],
                group_info["max_member_count"],
                group_info["member_count"],
            )
            logger.info(f"自动更新群组 {g} 信息成功")
    except Exception as e:
        logger.error(f"自动更新群组信息错误 e:{e}")


# 定时更新好友信息
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=1,
)
async def _():
    try:
        bot = get_bot()
        fl = await bot.get_friend_list()
        for f in fl:
            if await FriendUser.add_friend_info(f["user_id"], f["nickname"]):
                logger.info(f'自动更新好友 {f["user_id"]} 信息成功')
            else:
                logger.warning(f'自动更新好友 {f["user_id"]} 信息失败')
    except Exception as e:
        logger.error(f"自动更新群组信息错误 e:{e}")


# 自动备份
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=25,
)
async def _():
    if Config.get_config("_backup", "BACKUP_FLAG"):
        _backup_path = Path() / 'backup'
        _backup_path.mkdir(exist_ok=True, parents=True)
        for x in Config.get_config("_backup", "BACKUP_DIR_OR_FILE"):
            try:
                path = Path(x)
                _p = _backup_path / x
                if path.exists():
                    if path.is_dir():
                        if _p.exists():
                            shutil.rmtree(_p, ignore_errors=True)
                        shutil.copytree(x, _p)
                    else:
                        if _p.exists():
                            _p.unlink()
                        shutil.copy(x, _p)
                    logger.info(f'已完成自动备份：{x}')
            except Exception as e:
                logger.error(f"自动备份文件 {x} 发生错误 {type(e)}:{e}")
