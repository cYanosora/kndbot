from asyncpg.exceptions import (
    DuplicateColumnError,
    UndefinedColumnError,
    PostgresSyntaxError,
)
import nonebot
from nonebot import Driver

from configs.path_config import TEXT_PATH
from services.db_context import db
from services.log import logger
from utils.http_utils import AsyncHttpx
from utils.utils import scheduler

try:
    import ujson as json
except ModuleNotFoundError:
    import json


driver: Driver = nonebot.get_driver()


@driver.on_startup
async def update_city():
    """
    部分插件需要中国省份城市
    这里直接更新，避免插件内代码重复
    """
    china_city = TEXT_PATH / "china_city.json"
    data = {}
    if not china_city.exists():
        try:
            res = await AsyncHttpx.get(
                "http://www.weather.com.cn/data/city3jdata/china.html", timeout=5
            )
            res.encoding = "utf8"
            provinces_data = json.loads(res.text)
            for province in provinces_data.keys():
                data[provinces_data[province]] = []
                res = await AsyncHttpx.get(
                    f"http://www.weather.com.cn/data/city3jdata/provshi/{province}.html",
                    timeout=5,
                )
                res.encoding = "utf8"
                city_data = json.loads(res.text)
                for city in city_data.keys():
                    data[provinces_data[province]].append(city_data[city])
            with open(china_city, "w", encoding="utf8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info("自动更新城市列表完成.....")
        except TimeoutError:
            logger.warning("自动更新城市列表超时.....")
        except ValueError:
            logger.warning("自动城市列表失败.....")
        except Exception as e:
            logger.error(f"自动城市列表未知错误 {type(e)}：{e}")


@driver.on_startup
async def _():
    """
    数据库表结构变换
    """
    _flag = []
    sql_str = [
        # (
        #     "ALTER TABLE pjsk_bind ADD pjsk_type Integer NOT NULL DEFAULT 0;",
        #     "pjsk_bind",
        # ),  # pjsk_bind 表添加一个 pjsk_type 字段
        # (
        #     "ALTER TABLE pjsk_bind ADD isprivate Boolean NOT NULL DEFAULT False;",
        #     "pjsk_bind",
        # ),  # pjsk_bind 表添加一个 isprivate 字段(
        #
        # (
        #     "UPDATE pjsk_bind SET pjsk_type=0;",
        #     "pjsk_bind",
        # ),  # pjsk_bind 表添加一个 isprivate 字段
        # (
        #     "UPDATE pjsk_bind SET isprivate=False;",
        #     "pjsk_bind",
        # ),  # pjsk_bind 表添加一个 isprivate 字段

        # (
        #     "ALTER TABLE sign_group_users ADD sign_items json NOT NULL DEFAULT '{}';",
        #     "sign_group_users",
        # ),  # sign_group_users 表添加一个 sign_item 字段
        #
        # (
        #     "ALTER TABLE sign_group_users rename specify_probability To extra_impression;",
        #     "sign_group_users",
        # ),  # 将 sign_group_users 的 specify_probability 改为 extra_impression
        # (
        #     "ALTER TABLE sign_group_users ADD impression_promoted_time timestamp with time zone;",
        #     "sign_group_users"
        # ),  # sign_group_users 表添加一个 impression_promoted_time 字段
    ]
    for sql in sql_str:
        try:
            flag = sql[1]
            sql = sql[0]
            query = db.text(sql)
            await db.first(query)
            logger.info(f"完成sql操作：{sql}")
            _flag.append(flag)
        except (DuplicateColumnError, UndefinedColumnError):
            pass
        except PostgresSyntaxError:
            logger.error(f"语法错误：执行sql失败：{sql}")
    # 完成后
    end_sql_str = [
        # "ALTER TABLE sign_group_users DROP COLUMN add_probability;"
        # 删除 sign_group_users 的 add_probability 字段
    ]
    for sql in end_sql_str:
        try:
            query = db.text(sql)
            await db.first(query)
            logger.info(f"完成执行sql操作：{sql}")
        except (DuplicateColumnError, UndefinedColumnError):
            pass
        except PostgresSyntaxError:
            logger.error(f"语法错误：执行sql失败：{sql}")


# 自动更新城市列表
@scheduler.scheduled_job(
    "cron",
    hour=6,
    minute=1,
)
async def _():
    await update_city()
    logger.info("已自动更新城市列表！")
