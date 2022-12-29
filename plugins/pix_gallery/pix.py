import asyncio
from typing import Tuple
from nonebot.internal.matcher import Matcher
from nonebot.permission import SUPERUSER
from utils.limit_utils import access_count, access_cd
from utils.utils import is_number
from manager import Config
from ._model.omega_pixiv_illusts import OmegaPixivIllusts
from utils.message_builder import image, custom_forward_msg
from manager import withdraw_message_manager
from services.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, Message, GROUP
from nonebot.params import CommandArg, Command
from ._data_source import get_image, gen_keyword_pic, get_keyword_num, uid_pid_exists
from ._model.pixiv import Pixiv
from ._model.pixiv_keyword_user import PixivKeywordUser
from nonebot import on_command
import random


__plugin_name__ = "pix"
__plugin_type__ = "好康的"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    查看 pix图库 图片
    指令：
        pix ?*[tags]: 通过 tag 获取相似图片，不含tag时随机抽取，tag需添加才能使用
        pix [pid]: 查看图库中指定pid图片
    ----------------------------------------------------
    查看pix图库
    指令：
        查看pix图库 ?[tags]: 查看指定tag图片数量，为空时查看整个图库
        显示pix关键词: 查看pix已有关键词
        我的pix关键词: 查看自己提供的关键词
    ----------------------------------------------------
    PIX关键词/UID/PID添加管理操作(需要bot主审核通过后才能使用)
    指令：
        添加pix关键词 [Tag]: 添加一个pix搜索收录Tag
        添加pixuid [uid]: 添加一个pix搜索收录uid
        添加pixpid [pid]: 添加一个pix收录pid
""".strip()
__plugin_superuser_usage__ = """
usage：
    超级用户额外的 pix 指令
    指令：
        pix -s ?*[tags]: 通过tag获取色图，不含tag时随机
        pix -r ?*[tags]: 通过tag获取r18图，不含tag时随机
""".strip()
__plugin_settings__ = {
    "cmd": ["pix", "Pix", "PIX", "添加pix关键词"],
}
__plugin_cd_limit__ = {"cd": 10, "rst": "别急，[cd]s后再用！[at]",}
__plugin_block_limit__ = {"rst": "您有PIX图片正在处理，请稍等..."}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "今天已经看够了吧，还请明天再继续呢[at]",
}
__plugin_configs__ = {
    "MAX_ONCE_NUM2FORWARD": {
        "value": 5,
        "help": "单次发送的图片数量达到指定值时转发为合并消息",
        "default_value": 5,
    }
}


PIX_RATIO = None
OMEGA_RATIO = None

pix = on_command("pix", aliases={"PIX", "Pix"}, priority=5, permission=GROUP, block=True)

my_keyword = on_command("我的pix关键词", aliases={"我的pix关键字"}, permission=GROUP, priority=5, block=True)

show_keyword = on_command("显示pix关键词", aliases={"显示pix关键字"}, permission=GROUP, priority=5, block=True)

show_pix = on_command("查看pix图库", priority=5, permission=GROUP, block=True)

add_keyword = on_command("添加pix关键词", aliases={"添加pix关键字"}, priority=5, permission=GROUP, block=True)

# 超级用户可以通过字符 -f 来强制收录不检查是否存在
add_uid_pid = on_command("添加pixuid", priority=5, permission=GROUP, block=True)

add_black_pid = on_command("添加pix黑名单", permission=SUPERUSER, priority=5, block=True)


@pix.handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    global PIX_RATIO, OMEGA_RATIO
    if PIX_RATIO is None:
        pix_omega_pixiv_ratio = Config.get_config("pix", "PIX_OMEGA_PIXIV_RATIO")
        PIX_RATIO = pix_omega_pixiv_ratio[0] / (
            pix_omega_pixiv_ratio[0] + pix_omega_pixiv_ratio[1]
        )
        OMEGA_RATIO = 1 - PIX_RATIO
    num = 1
    keyword = arg.extract_plain_text().strip()
    x = keyword.split()
    if "-s" in x:
        x.remove("-s")
        nsfw_tag = 1
    elif "-r" in x:
        x.remove("-r")
        nsfw_tag = 2
    else:
        nsfw_tag = 0
    if nsfw_tag != 0 and str(event.user_id) not in bot.config.superusers:
        await pix.finish("你不能看这些噢，这些图片看了对身体不好...")
    if n := len(x) == 1 and is_number(x[0]):
        num = int(x[-1])
        keyword = ""
    elif n > 1:
        if is_number(x[-1]):
            num = int(x[-1])
            if num > 10:
                if str(event.user_id) not in bot.config.superusers or (
                    str(event.user_id) in bot.config.superusers and num > 30
                ):
                    num = random.randint(1, 10)
                    await pix.send(f"太贪心了，就给你发{num}张好了")
            x = x[:-1]
            keyword = " ".join(x)
    pix_num = int(num * PIX_RATIO) + 15 if PIX_RATIO != 0 else 0
    omega_num = num - pix_num + 15
    if is_number(keyword):
        if num == 1:
            pix_num = 15
            omega_num = 15
        all_image = await Pixiv.query_images(
            uid=int(keyword), num=pix_num, r18=1 if nsfw_tag == 2 else 0
        ) + await OmegaPixivIllusts.query_images(
            uid=int(keyword), num=omega_num, nsfw_tag=nsfw_tag
        )
    elif keyword.lower().startswith("pid"):
        pid = keyword.replace("pid", "").replace(":", "").replace("：", "")
        if not is_number(pid):
            await pix.finish("PID必须是数字...", at_sender=True)
        all_image = await Pixiv.query_images(
            pid=int(pid), r18=1 if nsfw_tag == 2 else 0
        )
        if not all_image:
            all_image = await OmegaPixivIllusts.query_images(
                pid=int(pid), nsfw_tag=nsfw_tag
            )
    else:
        tmp = await Pixiv.query_images(
            x, r18=1 if nsfw_tag == 2 else 0, num=pix_num
        ) + await OmegaPixivIllusts.query_images(x, nsfw_tag=nsfw_tag, num=omega_num)
        tmp_ = []
        all_image = []
        for x in tmp:
            if x.pid not in tmp_:
                all_image.append(x)
                tmp_.append(x.pid)
    if not all_image:
        await pix.finish(f"未在图库中找到与 {keyword} 相关Tag/UID/PID的图片...", at_sender=True)
    msg_list = []
    for _ in range(num):
        img_url = None
        author = None
        # if not all_image:
        #     await pix.finish("坏了...发完了，没图了...")
        img = random.choice(all_image)
        all_image.remove(img)
        if isinstance(img, OmegaPixivIllusts):
            img_url = img.url
            author = img.uname
        elif isinstance(img, Pixiv):
            img_url = img.img_url
            author = img.author
        pid = img.pid
        title = img.title
        uid = img.uid
        _img = await get_image(img_url, event.user_id)
        if _img:
            if Config.get_config("pix", "SHOW_INFO"):
                msg_list.append(
                    Message(
                        f"title：{title}\n"
                        f"author：{author}\n"
                        f"PID：{pid}\nUID：{uid}\n"
                        f"{image(_img)}"
                    )
                )
            else:
                msg_list.append(image(_img))
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 查看PIX图库PID: {pid}"
            )
        else:
            msg_list.append("这张图似乎下载失败了")
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 查看PIX图库PID: {pid}，下载图片出错"
            )
    if (
        Config.get_config("pix", "MAX_ONCE_NUM2FORWARD")
        and num >= Config.get_config("pix", "MAX_ONCE_NUM2FORWARD")
        and isinstance(event, GroupMessageEvent)
    ):
        access_cd(matcher.plugin_name, event)
        access_count(matcher.plugin_name, event)
        msg_id = await bot.send_group_forward_msg(
            group_id=event.group_id, messages=custom_forward_msg(msg_list, bot.self_id)
        )
        withdraw_message_manager.withdraw_message(
            event, msg_id, Config.get_config("pix", "WITHDRAW_PIX_MESSAGE")
        )
    else:
        access_cd(matcher.plugin_name, event)
        access_count(matcher.plugin_name, event)
        for msg in msg_list:
            msg_id = await pix.send(msg)
            withdraw_message_manager.withdraw_message(
                event, msg_id, Config.get_config("pix", "WITHDRAW_PIX_MESSAGE")
            )


@add_keyword.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    group_id = -1
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    if msg:
        if await PixivKeywordUser.add_keyword(
            event.user_id, group_id, msg, bot.config.superusers
        ):
            await add_keyword.send(
                f"已成功添加pixiv搜图关键词：{msg}，请等待管理员通过该关键词！", at_sender=True
            )
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 添加了pixiv搜图关键词:" + msg
            )
        else:
            await add_keyword.finish(f"该关键词 {msg} 已存在...")
    # else:
    #     await add_keyword.finish(f"虚空关键词？.？.？.？")


@add_uid_pid.handle()
async def _(bot: Bot, event: MessageEvent, cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    exists_flag = True
    if msg.find("-f") != -1 and str(event.user_id) in bot.config.superusers:
        exists_flag = False
        msg = msg.replace("-f", "").strip()
    if msg:
        for msg in msg.split():
            if not is_number(msg):
                await add_uid_pid.finish("UID只能是数字呢...", at_sender=True)
            if cmd[0].lower().endswith("uid"):
                msg = f"uid:{msg}"
            else:
                msg = f"pid:{msg}"
                if await Pixiv.check_exists(int(msg[4:]), "p0"):
                    await add_uid_pid.finish(f"该PID：{msg[4:]}已存在...", at_sender=True)
            if not await uid_pid_exists(msg) and exists_flag:
                await add_uid_pid.finish("画师或作品不存在或搜索正在CD，请稍等...", at_sender=True)
            group_id = -1
            if isinstance(event, GroupMessageEvent):
                group_id = event.group_id
            if await PixivKeywordUser.add_keyword(
                event.user_id, group_id, msg, bot.config.superusers
            ):
                await add_uid_pid.send(
                    f"已成功添加pixiv搜图UID/PID：{msg[4:]}，请等待bot主通过！", at_sender=True
                )
            else:
                await add_uid_pid.finish(f"该UID/PID：{msg[4:]} 已存在...")
    # else:
    #     await add_uid_pid.finish("湮灭吧！虚空的UID！")

@my_keyword.handle()
async def _(event: MessageEvent):
    data = await PixivKeywordUser.get_all_user_dict()
    if data.get(event.user_id) is None or not data[event.user_id]["keyword"]:
        await my_keyword.finish("您目前没有提供任何Pixiv搜图关键字...", at_sender=True)
    await my_keyword.send(
        f"您目前提供的如下关键字：\n\t" + "，".join(data[event.user_id]["keyword"])
    )


@show_keyword.handle()
async def _(bot: Bot, event: MessageEvent):
    _pass_keyword, not_pass_keyword = await PixivKeywordUser.get_current_keyword()
    if _pass_keyword or not_pass_keyword:
        await show_keyword.send(
            image(
                b64=await asyncio.get_event_loop().run_in_executor(
                    None,
                    gen_keyword_pic,
                    _pass_keyword,
                    not_pass_keyword,
                    str(event.user_id) in bot.config.superusers,
                )
            )
        )
    else:
        if str(event.user_id) in bot.config.superusers:
            await show_keyword.finish(f"目前没有已收录或待收录的搜索关键词...")
        else:
            await show_keyword.finish(f"目前没有已收录的搜索关键词...")


@show_pix.handle()
async def _(arg: Message = CommandArg()):
    keyword = arg.extract_plain_text().strip()
    count, r18_count, count_, setu_count, r18_count_ = await get_keyword_num(keyword)
    await show_pix.send(
        f"PIX图库：{keyword}\n"
        f"总数：{count + r18_count}\n"
        f"美图：{count}\n"
        f"不可以涩涩的图：{r18_count}"
        # f"---------------\n"
        # f"Omega图库：{keyword}\n"
        # f"总数：{count_ + setu_count + r18_count_}\n"
        # f"美图：{count_}\n"
        # f"色图：{setu_count}\n"
        # f"R18：{r18_count_}"
    )


@add_black_pid.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    pid = arg.extract_plain_text().strip()
    if pid:
        img_p = ""
        if "p" in pid:
            img_p = pid.split("p")[-1]
            pid = pid.replace("_", "")
            pid = pid[: pid.find("p")]
        if not is_number(pid):
            await add_black_pid.finish("PID必须全部是数字！", at_sender=True)
        if await PixivKeywordUser.add_keyword(
            114514,
            114514,
            f"black:{pid}{f'_p{img_p}' if img_p else ''}",
            bot.config.superusers,
        ):
            await add_black_pid.send(f"已添加PID：{pid} 至黑名单中...")
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
                f" 添加了pixiv搜图黑名单 PID:{pid}"
            )
        else:
            await add_black_pid.send(f"PID：{pid} 已添加黑名单中，添加失败...")
