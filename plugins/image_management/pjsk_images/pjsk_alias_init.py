from datetime import datetime
from services import logger

from .pjsk_config import pjsk_info_mapping
from .pjsk_db_source import PjskAlias


async def init_default_pjsk_alias():
    """
    导入初始别名
    """
    # 初始检测，只执行一次
    for name, alias in pjsk_info_mapping.items():
        if not await PjskAlias.check_name_exists(name):
            await PjskAlias.add_alias(name, alias, 114514, 114514, datetime.now(), True)
    logger.info("[pjsk]数据库完成了首次初始化！之后不再初始化！")
