from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, Message, GROUP
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot import on_command
from utils.limit_utils import access_cd, access_count
from utils.utils import is_number
from .data_source import get_pixiv_urls, download_pixiv_imgs, search_pixiv_urls, search_pixiv_url_byid
from services.log import logger
from nonebot.adapters.onebot.v11.exception import NetworkError
from asyncio.exceptions import TimeoutError
from utils.message_builder import custom_forward_msg
from manager import Config
from typing import Type
import time

__plugin_name__ = "P站排行/搜图"
__plugin_type__ = "好康的"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    P站排行：
        可选参数：
        类型：
            1. 日排行
            2. 周排行
            3. 月排行
            4. 原创排行
            5. 新人排行
        p站排行 ?[参数] ?[数量] ?[日期]
        示例：
            p站排行   [无参数默认为日榜]
            p站排行 1
            p站排行 1 5
            p站排行 1 5 2018-4-25
        【注意空格！！】【在线搜索会较慢】
    ---------------------------------
    P站搜图：
        搜图 [pid]/[关键词] ?[数量] ?[页数=1]
        示例：
            搜图 97692724
            搜图 宵崎奏
            搜图 宵崎奏 5
        【默认为 热度排序】
        【tag间注意空格！！】【在线搜索会较慢】【数量可能不符？可能该页数量不够，也可能被R-18屏蔽】(拒绝色色！)
""".strip()
__plugin_settings__ = {
    "cmd": ["p站排行", "P站排行", "搜图"],
}
__plugin_cd_limit__ = {"cd": 45, "rst": "搜图好累，不干了，歇[cd]秒...",}
__plugin_block_limit__ = {"rst": "P站排行或搜图正在进行中，请不要重复触发命令..."}
__plugin_count_limit__ = {
    "max_count": 5,
    "limit_type": "user",
    "rst": "今天累了，不给你搜了[at]",
}
__plugin_configs__ = {
    "TIMEOUT": {
        "value": 10,
        "help": "图片下载超时限制",
        "default_value": 10
    },
    "MAX_PAGE_LIMIT": {
        "value": 20,
        "help": "作品最大页数限制，超过的作品会被略过",
        "default_value": 20
    }
}
Config.add_plugin_config(
    "hibiapi",
    "HIBIAPI",
    "https://api.obfs.dev",
    help_="如果没有自建或其他hibiapi请不要修改",
    default_value="https://api.obfs.dev",
)
Config.add_plugin_config(
    "pixiv",
    "PIXIV_NGINX_URL",
    "i.pixiv.re",
    help_="Pixiv反向代理"
)


rank_dict = {
    "1": "day",
    "2": "week",
    "3": "month",
    "4": "week_original",
    "5": "week_rookie",
    # "6": "day_r18",
    # "7": "week_r18",
    # "8": "day_male_r18",
    # "9": "week_r18g",
}


pixiv_rank = on_command(
    "p站排行",
    aliases={"P站排行"},
    priority=5,
    permission=GROUP,
    block=True,
)
pixiv_keyword = on_command("搜图", priority=5, permission=GROUP, block=True)


@pixiv_rank.handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip().strip()
    msg = msg.split(" ")
    msg = [m for m in msg if m]
    code = 0
    info_list = []
    if not msg:
        msg = ["1"]
    # if msg[0] in ["6", "7", "8", "9"]:
    #     if event.message_type == "group":
    #         await pixiv_rank.finish("羞羞脸！私聊里自己看！", at_sender=True)
    if (n := len(msg)) == 0 or msg[0] == "":
        info_list, code = await get_pixiv_urls(rank_dict.get("1"))
    elif n == 1:
        if msg[0] not in ["1", "2", "3", "4", "5"]:
            await pixiv_rank.finish("要好好输入要看什么类型的排行榜呀！", at_sender=True)
        info_list, code = await get_pixiv_urls(rank_dict.get(msg[0]))
    elif n == 2:
        info_list, code = await get_pixiv_urls(rank_dict.get(msg[0]), int(msg[1]))
    elif n == 3:
        if not check_date(msg[2]):
            await pixiv_rank.finish("日期格式错误了", at_sender=True)
        info_list, code = await get_pixiv_urls(
            rank_dict.get(msg[0]), int(msg[1]), date=msg[2]
        )
    else:
        await pixiv_rank.finish("格式错了噢，参数不够？看看帮助？", at_sender=True)
    if code != 200 and info_list:
        await pixiv_rank.finish(info_list[0])
    if not info_list:
        await pixiv_rank.finish("没有找到啊，等等再试试吧~V", at_sender=True)
    access_cd(matcher.plugin_name, event)
    access_count(matcher.plugin_name, event)
    await send_image(info_list, pixiv_rank, bot, event)
    logger.info(
        f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
        f" 查看了P站排行榜 code：{msg[0]}"
    )


@pixiv_keyword.handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await pixiv_keyword.finish("什..什么都没有给我，怎么搜嘛...", at_sender=True)
    # pid搜图
    if is_number(msg) and len(msg) == 8:
        info_list, code = await search_pixiv_url_byid(int(msg))
        if code != 200:
            await pixiv_keyword.finish(info_list[0], at_sender=True)
        if not info_list:
            await pixiv_keyword.finish("没有找到啊，等等再试试吧~V", at_sender=True)

        access_cd(matcher.plugin_name, event)
        access_count(matcher.plugin_name, event)
        await send_image(info_list, pixiv_keyword, bot, event)
        logger.info(
            f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
            f" 查看了pid {msg}"
        )
    # rank、keyword搜图
    else:
        if isinstance(event, GroupMessageEvent):
            if "r18" in msg.lower():
                await pixiv_keyword.finish("你不会害羞的嘛 八嘎！", at_sender=True)
        r18 = 0 if "r18" in msg.lower() else 1
        msg = msg.replace("r18", "").strip().split()
        msg = [m.strip() for m in msg if m]
        keyword = None
        info_list = None
        num = 10
        page = 1
        if (n := len(msg)) == 1:
            keyword = msg[0]
        if n > 1:
            if not is_number(msg[1]):
                await pixiv_keyword.finish("图片数量必须是数字！", at_sender=True)
            num = int(msg[1])
        if n > 2:
            if not is_number(msg[2]):
                await pixiv_keyword.finish("页数数量必须是数字！", at_sender=True)
            page = int(msg[2])
        if keyword:
            info_list, code = await search_pixiv_urls(keyword, num, page, r18)
            if code != 200:
                await pixiv_keyword.finish(info_list[0], at_sender=True)
        if not info_list:
            await pixiv_keyword.finish("没有找到啊，等等再试试吧~V", at_sender=True)
        access_cd(matcher.plugin_name, event)
        access_count(matcher.plugin_name, event)
        await send_image(info_list, pixiv_keyword, bot, event)
        logger.info(
            f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
            f" 查看了搜索 {keyword} R18：{r18}"
        )


def check_date(date):
    try:
        time.strptime(date, "%Y-%m-%d")
        return True
    except:
        return False


async def send_image(
    info_list: list, matcher: Type[Matcher], bot: Bot, event: MessageEvent
):
    if isinstance(event, GroupMessageEvent):
        await pixiv_rank.send("开始下载整理图片...请耐心等待(－ω－)")
        idx = 0
        mes_list = []
        for title, author, urls in info_list:
            try:
                _message = f"title: {title}\nauthor: {author}\n" + await download_pixiv_imgs(urls, event.user_id, idx)
            except:
                _message = "这张图被网络炸掉了！"
            mes_list.append(_message)
            idx += 1
        if len(mes_list) == 1:
            await bot.send_group_msg(group_id=event.group_id, message=mes_list[0])
        else:
            mes_list = custom_forward_msg(mes_list, bot.self_id)
            await pixiv_rank.send("排行榜图片整理完毕(｡･ω･)", at_sender=True)
            await bot.send_group_forward_msg(group_id=event.group_id, messages=mes_list)
    else:
        for title, author, urls in info_list:
            try:
                await matcher.send(
                    f"title: {title}\n"
                    f"author: {author}\n"
                    + await download_pixiv_imgs(urls, event.user_id)
                )
            except (NetworkError, TimeoutError):
                await matcher.send("这张图被网络炸掉了！", at_sender=True)
