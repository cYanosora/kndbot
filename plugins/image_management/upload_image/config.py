import datetime
from services import logger
from utils.utils import scheduler
from .data_source import get_local_record

global_record = {
    'num': 0,
    'date': datetime.datetime.strftime(datetime.datetime.now(),'%Y/%m/%d')
}


# 每天定时更新日期
@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=5,
)
async def _():
    global global_record
    global_record['num'] = await get_local_record()
    global_record['date'] = datetime.datetime.strftime(datetime.datetime.now(), '%Y/%m/%d')
    logger.info(f"[定时任务]:更新pjsk日期、收录数成功")