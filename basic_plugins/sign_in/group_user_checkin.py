from datetime import datetime, timedelta
from nonebot import require
from models.sign_group_user import SignGroupUser
from models.group_member_info import GroupInfoUser
from models.bag_user import BagUser
from configs.config import NICKNAME
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent, Message
from utils.imageutils import BuildImage as IMG, Text2Image, text2image, pic2b64
from services.db_context import db
from utils.message_builder import image
from .utils import get_card, SIGN_TODAY_CARD_PATH, get_level_and_next_impression, clear_sign_view_pic, \
    clear_sign_sign_pic
from typing import Optional, Union
from nonebot.adapters.onebot.v11 import Bot
from services.log import logger
from .random_event import random_event
from utils.data_utils import init_rank
from utils.utils import get_user_avatar, GDict
from io import BytesIO
import random
import math
import asyncio
import secrets
import os
require('shop')
require("use")
from basic_plugins.shop.use.data_source import effect
GDict['run_sql'].append("ALTER TABLE sign_group_users ADD COLUMN continued_sign_items JSON default '{}' NOT NULL;")


# 用户单个群签到处理
async def group_user_check_in(bot: Bot, event: GroupMessageEvent) -> MessageSegment:
    nickname = event.sender.card or event.sender.nickname
    present = datetime.now()
    async with db.transaction():
        # 取得相应用户
        user = await SignGroupUser.ensure(event.user_id, event.group_id, for_update=True)
        # 如果同一天签到过，特殊处理
        if (    # +8小时是因为数据库中存的时间带时区属性，默认为格林尼治时间，需要转为东八区时间
            (user.checkin_time_last + timedelta(hours=8)).date() >= present.date()
            or f"{event.user_id}_{event.group_id}_sign_{present.date()}.png"
                in os.listdir(SIGN_TODAY_CARD_PATH)
        ):
            gold = await BagUser.get_gold(event.user_id, event.group_id)
            res = await get_card(user, nickname, None, gold, "")
        else:
            res = await _handle_check_in(bot, event, present)
        return res


# 用户所有群签到处理
async def check_in_all(bot: Bot, event: GroupMessageEvent):
    """
    说明:
        签到所有群
    参数:
        :param bot: Bot
        :param event: 签到事件
    """
    async with db.transaction():
        present = datetime.now()
        for u in await SignGroupUser.get_user_all_data(event.user_id):
            group = u.group_id
            if not (
                (u.checkin_time_last + timedelta(hours=32)).date() > present.date()
                or f"{u}_{group}_sign_{present.date()}"
                in os.listdir(SIGN_TODAY_CARD_PATH)
            ):
                await _handle_check_in(bot, event, present, group)


# 生成签到详细信息
async def _handle_check_in(
    bot: Bot, event: GroupMessageEvent, present: datetime, gid: int = None
) -> MessageSegment:
    group = gid if gid else event.group_id
    nickname = event.sender.card or event.sender.nickname
    user_qq = event.user_id
    user = await SignGroupUser.ensure(user_qq, group, for_update=True)
    sign_items: dict = user.sign_items
    continued_items: dict = user.continued_sign_items
    property_ = await BagUser.get_property(user_qq, group)
    # 若无乐谱道具时
    if '乐谱' not in continued_items.keys():
        # 未使用好感双倍卡道具时自动使用
        if property_:
            for item in sign_items:
                if item.startswith("好感双倍卡"):
                    break
            else:
                for item in ["好感双倍卡1", "好感双倍卡2", "好感双倍卡3"]:
                    if item in property_.keys():
                        if await BagUser.delete_property(user_qq, group, item, 1):
                            await effect(bot, event, item, 1, "", event.message)
                            sign_items[item] = 1
                            break
    # 有乐谱道具时，删除所有好感双倍卡道具，并返还
    else:
        for used_item in sign_items.copy().keys():
            if used_item.startswith("好感双倍卡"):
                print(used_item, sign_items[used_item])
                await BagUser.add_property(user_qq, group, used_item, sign_items[used_item])
                del sign_items[used_item]

    # 杯面道具的额外好感
    impression_added = (secrets.randbelow(99) + 1) / 100
    logger.info(
        f"(用户{user.user_qq}, 群组 {user.group_id})"
        f"签到原始好感随机值：{impression_added:.2f} "
    )
    # 如果用户存在康乃馨
    extra_items = {}
    extra_impression = user.extra_impression
    extra_impression += sign_items.get("互动加成", 0) * 0.01
    impression_added += extra_impression
    # 双倍卡的额外好感
    critx2 = random.random()
    add_probability = user.add_probability
    is_double = False
    # 乐谱的加成
    if '乐谱' in continued_items.keys():
        impression_added *= 2
        extra_items['乐谱'] = continued_items['乐谱']
        is_double = True
    elif critx2 + add_probability > 0.97:
        impression_added *= 2
        is_double = True
    # 康乃馨的加成
    if "康乃馨" in property_.keys():
        item_impr_add = 0.06*impression_added
        extra_items["康乃馨"] = item_impr_add
        impression_added += item_impr_add
    # 签到记录进数据库
    await SignGroupUser.sign(user, impression_added, present)
    # 生成签到随机事件，记录进数据库
    gold = random.randint(1, 100)
    gift, gift_type = random_event(user.impression)
    if gift_type == "gold":
        gold += gift
        gift = f"额外金币 + {gift}"
    else:
        await BagUser.add_property(user_qq, group, gift)
        gift += ' + 1'
    # 八音盒的加成
    if "八音盒" in property_.keys():
        item_gold_add = round(gold * 0.25)
        extra_items["八音盒"] = item_gold_add
        gold += item_gold_add
    # 奏生日7天内集体+360金币
    nowdate = datetime.now().date()
    if nowdate.month == 2 and 10 <= nowdate.day <= 16:
        gold += 360
    # 加金币
    await BagUser.add_gold(user_qq, group, gold)

    # 日志记录以及生成签到图片
    logger_extra = f"受到被动道具("+'、'.join(extra_items.keys())+")加成" if extra_items else ""
    logger.info(
        f"(用户 {user.user_qq}, 群组 {user.group_id})"
        f" 签到成功，好感度: {user.impression:.2f} (+{impression_added:.2f})"
        f"获取金币：{gold + int(gift) if gift == 'gold' else gold}"
        f"获得道具：{gift if gift != 'gold' else '无'}"+
        logger_extra
    )
    if is_double:
        return await get_card(user, nickname, impression_added, gold, gift, sign_items, True, False, extra_items)
    else:
        return await get_card(user, nickname, impression_added, gold, gift, sign_items, False, False, extra_items)


# 用户单个群补签处理
async def group_user_recheck_in(bot: Bot, event: GroupMessageEvent, gid: int = None) -> Union[Message, str]:
    user_id = event.user_id
    group_id = event.group_id if not gid else gid

    # 获得签到用户以及bot可补签的天数
    property_ = await BagUser.get_property(user_id, group_id)

    user = await SignGroupUser.ensure(user_id, group_id, for_update=True)
    botinfo = await GroupInfoUser.get_member_info(int(bot.self_id), group_id)
    present = datetime.now()
    # 今日已经签到，补签天数计入今日
    # print('上次签到日期:',(user.checkin_time_last + timedelta(hours=8)).date())
    # print('当前日期:', present.date())
    if (  # 加8小时是因为时区要转换为东八区时间进行比较，数据库中存的时间取出来时默认为格林尼治时间
        (user.checkin_time_last + timedelta(hours=8)).date() >= present.date()
        or f"{user_id}_{group_id}_sign_{present.date()}.png"
            in os.listdir(SIGN_TODAY_CARD_PATH)
    ):
        # print('今日已经签到')
        avail_days = (present.date() - botinfo.user_join_time.date()).days - user.checkin_count + 1
        prep_reply = '。'
    # 今日尚未签到，补签天数不计入今日
    else:
        # print('今日尚未签到')
        avail_days = (present.date() - botinfo.user_join_time.date()).days - user.checkin_count
        prep_reply = '，不过你今天还没有签到呢。'
    # print('入群日期：', botinfo.user_join_time.date())
    # print('目前日期：', present.date())
    # print('相隔天数：', (present.date() - botinfo.user_join_time.date()).days)
    # print('已签天数：', user.checkin_count)
    # print('漏签天数：', avail_days)
    if avail_days <= 0:
        reply = f"你没有漏签的天数呢" + prep_reply
        return reply
    num = property_.get("补签卡", 0) if property_ else 0
    if num == 0:
        return "你没有补签卡哦"
    if num > avail_days:
        # print('使用道具大于漏签天数')
        resign_days = avail_days
    else:
        # print('使用道具小于等于漏签天数')
        resign_days = num
    await BagUser.delete_property(user_id, group_id, "补签卡", resign_days)

    # 开始补签
    add_impr = []
    add_coin = []
    add_item = []
    for i in range(resign_days):
        add_impr.append((secrets.randbelow(99) + 1) / 100)
        gold = random.randint(1, 100)
        gift, gift_type = random_event(user.impression)
        if gift_type == "gold":
            add_coin.append(gold + gift)
        else:
            add_coin.append(gold)
            add_item.append(gift)
    # 数据进数据库
    await BagUser.add_gold(user_id, group_id, sum(add_coin))
    await user.update(
        checkin_count=user.checkin_count + resign_days,
        impression=user.impression + sum(add_impr),
    ).apply()
    for item in add_item:
        await BagUser.add_property(user_id, group_id, item)
    # 反馈文本
    left_days = avail_days - resign_days
    resign_text = f"，你还剩{left_days}天未补签\n" if left_days > 0 else "，已完成所有补签\n"
    add_item_dict = {}
    for i in add_item:
        add_item_dict[i] = add_item_dict.get(i, 0) + 1
    item_text = "\n额外获得道具：" if add_item_dict else ""
    for i, j in add_item_dict.items():
        item_text += "{} × {}，".format(i, j)
    item_text = item_text[:-1] if item_text else ""
    if resign_days > 1:
        reward = f"合计好感度+{sum(add_impr):.2f}({'，'.join([str(i) for i in add_impr])})\n" \
                 f"合计金币+{sum(add_coin)}({'，'.join([str(i) for i in add_coin])})"
    else:
        reward = f"好感度+{sum(add_impr):.2f}，金币+{sum(add_coin)}"
    reply = f"补签{resign_days}天成功" + resign_text + reward + item_text
    # 清除好感度图片
    clear_sign_view_pic(user_id, group_id)
    # 日志记录
    logger.info(
        f"(USER {user_id}, GROUP {group_id})"
        f" RECHECKED IN successfully"
        f"好感+{sum(add_impr):.2f})，金币+{sum(add_coin)}"
        f'道具+({"，".join(add_item)})' if add_item else ''
    )
    reply = image(b64=pic2b64(text2image(reply)))
    return reply


# 用户所有群签到处理
async def recheck_in_all(bot: Bot, event: GroupMessageEvent):
    """
    说明:
        补签所有群
    参数:
        :param bot: Bot
        :param event: 补签事件
    """
    async with db.transaction():
        for u in await SignGroupUser.get_user_all_data(event.user_id):
            await group_user_recheck_in(bot, event, u.group_id)


# 设置好感度等级
async def setlevel(user_qq: int, group: int, level: int) -> bool:
    impr = await SignGroupUser.get_user_in_group_impr(user_qq, group)
    ori_level, _, _ = get_level_and_next_impression(impr)
    if int(ori_level) < level:
        return False
    await SignGroupUser.setlevel(user_qq, group, level)
    clear_sign_view_pic(user_qq, group)
    clear_sign_sign_pic(user_qq, group)
    return True


# 迁移用户数据
async def move_user_data(user_qq: int, src_group: int, tar_group: int = None):
    # 无指定群默认选择好感最高群
    if not tar_group:
        nodes = await SignGroupUser.get_user_all_data(user_qq)
        target_data = max(nodes, key=lambda item: item.impression)
        tar_group = target_data.group_id
    # 更换好感度数据
    try:
        await SignGroupUser.exchange_user_data(user_qq, src_group, tar_group)
        # 更换金币、道具数据
        await BagUser.exchange_user_data(user_qq, src_group, tar_group)
        # 清除签到图片
        clear_sign_view_pic(user_qq, src_group)
        clear_sign_sign_pic(user_qq, src_group)
        clear_sign_view_pic(user_qq, tar_group)
        clear_sign_sign_pic(user_qq, tar_group)
    except ValueError:
        raise ValueError("群号错误")


# 查看好感度
async def group_user_check(nickname: str, user_qq: int, group: int) -> MessageSegment:
    # heuristic: if users find they have never checked in they are probable to check in
    user = await SignGroupUser.ensure(user_qq, group)
    gold = await BagUser.get_gold(user_qq, group)
    items = user.sign_items
    extra_items = user.continued_sign_items
    property = await BagUser.get_property(user_qq, group)
    passive_items = ['康乃馨', '八音盒']
    for prop in passive_items:
        if prop in property.keys():
            extra_items[prop] = property[prop]
    return await get_card(user, nickname, None, gold, "", items=items, extra_items=extra_items, is_card_view=True)


# 查看好感排行
async def group_impression_rank(group: int, num: int) -> Optional[IMG]:
    user_qq_list, impression_list, _ = await SignGroupUser.get_all_impression(group)
    return await init_rank(
        "好感度排行榜", user_qq_list, impression_list, group, num, 50, f"g{group}_{num}_signrank"
    )


# 查看签到总榜
async def impression_rank(group_id: int, data: dict):
    user_qq_list, impression_list, group_list = await SignGroupUser.get_all_impression(
        group_id
    )
    users, impressions, groups = [], [], []
    num = 0
    for i in range(105 if len(user_qq_list) > 105 else len(user_qq_list)):
        impression = max(impression_list)
        index = impression_list.index(impression)
        user = user_qq_list[index]
        group = group_list[index]
        user_qq_list.pop(index)
        impression_list.pop(index)
        group_list.pop(index)
        if user not in users and impression < 100000:
            if user not in data["0"]:
                users.append(user)
                impressions.append(impression)
                groups.append(group)
            else:
                num += 1
    for i in range(num):
        impression = max(impression_list)
        index = impression_list.index(impression)
        user = user_qq_list[index]
        group = group_list[index]
        user_qq_list.pop(index)
        impression_list.pop(index)
        group_list.pop(index)
        if user not in users and impression < 100000:
            users.append(user)
            impressions.append(impression)
            groups.append(group)
    return (await asyncio.gather(*[_pst(users, impressions, groups)]))[0]


async def _pst(users: list, impressions: list, groups: list):
    lens = len(users)
    count = math.ceil(lens / 33)
    width = 10
    idx = 0
    A = IMG.new("RGBA", (1800, 3300), color="#FFE4C4")
    for _ in range(count):
        col_img = IMG.new("RGBA", (560, 3300), color="#FFE4C4")
        height = 0
        for _ in range(33 if int(lens / 33) >= 1 else lens % 33 - 1):
            idx += 1
            if idx > 100:
                break
            impression = max(impressions)
            index = impressions.index(impression)
            user = users[index]
            group = groups[index]
            impressions.pop(index)
            users.pop(index)
            groups.pop(index)
            try:
                user_name = (
                    await GroupInfoUser.get_member_info(user, group)
                ).user_name
            except AttributeError:
                user_name = f"我名字呢？"
            user_name = user_name if len(user_name) < 11 else user_name[:10] + "..."
            ava = await get_user_avatar(user)
            if ava:
                ava = IMG.open(BytesIO(ava)).resize((50, 50))
            else:
                ava = IMG.new("RGBA", (50, 50), color="white")
            ava.circle()
            #fontsize30
            bk = IMG.new("RGBA", (560, 100), color="#FFE4C4")
            bk_text_img = Text2Image.from_text(
                f"{idx}",
                fontsize=30,
                fontname="SourceHanSansCN-Regular.otf",
                ischeckchar=False
            ).to_image()
            font_w, font_h = bk_text_img.size
            bk.draw_text(
                (5, int((100 - font_h) / 2)),
                f"{idx}.",
                fontsize=30,
                fontname="SourceHanSansCN-Regular.otf",
                ischeckchar=False
            )
            bk.paste(ava, (55, int((100 - 50) / 2)), True)
            bk.draw_text(
                (120, int((100 - font_h) / 2)),
                f"{user_name}",
                fontsize=30,
                fontname="SourceHanSansCN-Regular.otf"
            )
            bk.draw_text(
                (460, int((100 - font_h) / 2)),
                f"[{impression:.2f}]",
                fontsize = 30,
                fontname = "SourceHanSansCN-Regular.otf",
                ischeckchar = False
            )

            col_img.paste(bk, (0, height))
            height += 100
        A.paste(col_img, (width, 0))
        lens -= 33
        width += 600
    W = IMG.new("RGBA", (1800, 3700), color="#FFE4C4")
    W.paste(A, (0, 260), True)
    textimg = Text2Image.from_text(
        f"{NICKNAME}的好感度总榜",
        fontsize=130,
        fontname="SourceHanSansCN-Regular.otf",
        ischeckchar=False
    ).to_image()
    font_w, font_h = textimg.size
    W.paste(textimg, (int((1800 - font_w) / 2), int((260 - font_h) / 2)), True)
    return W.pic2bs4()
