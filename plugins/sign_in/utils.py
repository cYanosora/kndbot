import io
from PIL import Image
from nonebot_plugin_htmlrender import template_to_pic
from .config import (
    SIGN_RESOURCE_PATH,
    SIGN_TODAY_CARD_PATH,
    lik2level,
    lik2relation,
    level2attitude,
)
from models.sign_group_user import SignGroupUser
from models.group_member_info import GroupInfoUser
from nonebot.adapters.onebot.v11 import MessageSegment
from utils.imageutils import BuildImage as IMG
from utils.message_builder import image
from configs.config import NICKNAME
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from nonebot import Driver
import nonebot
import os

driver: Driver = nonebot.get_driver()


@driver.on_startup
async def init_image():
    SIGN_RESOURCE_PATH.mkdir(parents=True, exist_ok=True)
    SIGN_TODAY_CARD_PATH.mkdir(exist_ok=True, parents=True)
    await GroupInfoUser.add_member_info(114514, 114514, "", datetime.min, 0)
    _u = await GroupInfoUser.get_member_info(114514, 114514)
    if _u.uid is None:
        await _u.update(uid=0).apply()
    generate_progress_bar_pic()
    clear_sign_data_pic()


async def get_card(
        user: "SignGroupUser",
        nickname: str,
        add_impression: Optional[float],
        gold: Optional[int],
        gift: str,
        items: dict = None,
        is_double: bool = False,
        is_card_view: bool = False,
) -> MessageSegment:
    user_id = user.user_qq
    date = datetime.now().date()
    _type = "view" if is_card_view else "sign"
    card_file = (
            Path(SIGN_TODAY_CARD_PATH)
            / f"{user_id}_{user.group_id}_{_type}_{date}.png"
    )
    # 若当天签到图片已存在直接返回，否则新生成签到图片
    if card_file.exists():
        return image(
            f"{user_id}_{user.group_id}_{_type}_{date}.png", "sign/today_card"
        )
    else:
        # 若好感加成为特殊值(-1)，代表生成好感度图片，否则生成签到图片
        if add_impression == -1:
            card_file = (
                    Path(SIGN_TODAY_CARD_PATH)
                    / f"{user_id}_{user.group_id}_view_{date}.png"
            )
            if card_file.exists():
                return image(
                    f"{user_id}_{user.group_id}_view_{date}.png",
                    "sign/today_card",
                )
            is_card_view = True
        # ava = BytesIO(await get_user_avatar(user_id))
        uid = await GroupInfoUser.get_group_member_uid(
            user.user_qq, user.group_id
        )
        # 查看好感度图片显示群内排名
        impression_list = None
        if is_card_view:
            _, impression_list, _ = await SignGroupUser.get_all_impression(
                user.group_id
            )
        return await _generate_card_render(
            user,
            nickname,
            add_impression,
            gold,
            gift,
            items,
            uid,
            impression_list,
            is_double,
            is_card_view,
        )


async def _generate_card_render(
    user: "SignGroupUser",
    nickname: str,
    impression: Optional[float],
    gold: Optional[int],
    gift: str,
    items: dict,
    uid: str,
    impression_list: List[float],
    is_double: bool = False,
    is_card_view: bool = False,
) -> MessageSegment:
    # 获取用户好感度相关信息
    level, next_impression, previous_impression = get_level_and_next_impression(user.impression)
    # 检查是否有固定好感度等级
    fixed_flag = False
    if user.custom_level is not None and user.custom_level >= 0:
        fixed_flag = True
        level = str(user.custom_level)
    # 检查是否有好感度等级加成
    promoted_flag = False
    if user.impression_promoted_time and user.impression_promoted_time.replace(tzinfo=None) + timedelta(hours=8) > datetime.now():
        promoted_flag = True
    # 暂时：对于等级高达4的用户做好感限制
    # 写好好感度5级的文案再开放
    if int(level) > 4:
        level = "4"
    elif promoted_flag and level == "4":
        promoted_flag = False

    # 生成des文字数据
    # 好感度已达max
    des = f"· 好感度等级：{level}" + \
        (
            f"+1 [{lik2relation[str(int(level)+1)]}]"
            if (promoted_flag and not fixed_flag and next_impression != 0)
            else f" [{lik2relation[level]}]"
        ) + \
        (" [被固定]" if fixed_flag else "")
    des += '\n'
    des += f"· {NICKNAME}对你的态度：" + \
        (
            f"{level2attitude[str(int(level)+1)]}"
            if (promoted_flag and not fixed_flag and next_impression != 0)
            else f"{level2attitude[level]}"
        )

    next_impression = user.impression if next_impression == 0 else next_impression
    des += '\n'
    des += f"· 距离升级还差 {next_impression - user.impression:.2f} 好感度" \
        if next_impression != user.impression \
        else f"· 已达最高等级"

    # 生成好感进度条偏差值数据
    bar_left_pos = -int(220*((next_impression - user.impression)/(next_impression - previous_impression)))

    # 生成uid数据
    if uid:
        uid = f"{uid}".rjust(12, "0")
        uid = uid[:4] + " " + uid[4:8] + " " + uid[8:]
    else:
        uid = "XXXX XXXX XXXX"
    uid = "UID: " + uid

    # 生成days数据
    days = user.checkin_count

    # 生成impr数据
    impr = f"{user.impression:.2f}"

    # 生成watermark数据
    watermark = f"{NICKNAME}@{datetime.now().year}"

    # 生成total、title文字数据
    if is_card_view:
        title = ""
        if impression_list:
            impression_list.sort(reverse=True)
            index = impression_list.index(user.impression)
            title = f"* 此群好感排名第 {index + 1} 位"
        total = ""
        total += f"上次签到日期：{'从未' if user.checkin_time_last == datetime.min else user.checkin_time_last.date()}\n"
        total += f"总金币：{gold}"
        _isSign = "view"
    else:
        total = ""
        title = "今日签到"
        impression_text = f"好感度合计 + {impression:.2f}"
        gold_text = f"  金币 + {gold}"
        total += impression_text + gold_text + '\n'
        # 生成touch、道具数据
        touch_text = ""
        if items:
            if "互动加成" in items:
                touch_text = f"(日常互动+{items.pop('互动加成') * 0.01})"
            items_text = ""
            _double_flag = True if is_double else False
            for item in items:
                items_text += f"已使用{item} × {items.get(item)}"
                if str(item).startswith("好感双倍") and is_double:
                    _double_flag = False
                    items_text += " (触发双倍)"
                elif str(item) == "杯面":
                    cup_count: int = int(items.get('杯面'))
                    if cup_count == 1:
                        items_text += " (+0.05)"
                    elif cup_count == 2:
                        items_text += " (+0.11)"
                    elif cup_count >= 3:
                        items_text += " (+0.18)"
                items_text += '\n'
            if _double_flag:
                touch_text += "(触发双倍)"
            total += items_text + touch_text
        elif is_double:
            total += "(触发双倍)"
        _isSign = True

    # 生成时间数据
    current_datetime_str = datetime.now().strftime("%Y-%m-%d %a %H:%M:%S")
    _time = f"时间：{current_datetime_str}"
    # 导入模板
    template_path = str(Path(__file__).parent / "templates")
    pic = await template_to_pic(
        template_path=template_path,
        template_name="sign.html",
        templates={
            "qq": user.user_qq,
            "nickname": nickname,
            "uid": uid,
            "days": days,
            "impr": impr,
            "des": des,
            "bar_left_pos": bar_left_pos,
            "time": _time,
            "title": title,
            "total": total,
            "gift": gift,
            "isGiftDisplay": str(_isSign),
            "watermark": watermark
        },
        pages={
            "viewport": {"width": 876, "height": 424},
            "base_url": f"file://{template_path}",
        },
        wait=0,
    )
    a = Image.open(io.BytesIO(pic))
    a.save(
        SIGN_TODAY_CARD_PATH /
        f"{user.user_qq}_{user.group_id}_{'sign' if _isSign else 'view'}_{datetime.now().date()}.png",
        format="PNG"
    )
    return MessageSegment.image(pic)


def generate_progress_bar_pic():
    bg_2 = (254, 1, 254)
    bg_1 = (0, 245, 246)

    bk = IMG.new("RGBA", (1000, 50))
    img_x = IMG.new("RGBA", (50, 50), color=bg_2).circle().crop((25, 0, 50, 50))
    img_y = IMG.new("RGBA", (50, 50), color=bg_1).circle().crop((0, 0, 25, 50))
    A = IMG.new("RGBA", (950, 50))
    width, height = A.size

    step_r = (bg_2[0] - bg_1[0]) / width
    step_g = (bg_2[1] - bg_1[1]) / width
    step_b = (bg_2[2] - bg_1[2]) / width

    for y in range(0, width):
        bg_r = round(bg_1[0] + step_r * y)
        bg_g = round(bg_1[1] + step_g * y)
        bg_b = round(bg_1[2] + step_b * y)
        for x in range(0, height):
            A.draw_point((y, x), fill=(bg_r, bg_g, bg_b))
    bk.paste(img_y, (0, 0), True)
    bk.paste(A, (25, 0), True)
    bk.paste(img_x, (975, 0), True)
    bk.save_file(SIGN_RESOURCE_PATH / "bar.png")

    A = IMG.new("RGB", (950, 50), color="white")
    bk = IMG.new("RGBA", (1000, 50))
    img_x = IMG.new("RGB", (50, 50), color="white").circle().crop((25, 0, 50, 50))
    img_y = IMG.new("RGB", (50, 50), color="white").circle().crop((0, 0, 25, 50))
    bk.paste(img_y, (0, 0))
    bk.paste(A, (25, 0))
    bk.paste(img_x, (975, 0))
    bk.save_file(SIGN_RESOURCE_PATH / "bar_white.png")


# 返回：好感度等级，下个等级的好感度需求，当前等级的好感度需求
def get_level_and_next_impression(impression: float):
    if impression == 0:
        return lik2level[0], 10, 0
    keys = list(lik2level.keys())
    for i in range(len(keys)):
        if impression > keys[i]:
            return lik2level[keys[i]], keys[i - 1], keys[i]
    return lik2level[0], 10, 0


def clear_sign_view_pic(user_id: int, group_id: int):
    date = datetime.now().date()
    file = Path(SIGN_TODAY_CARD_PATH) / f"{user_id}_{group_id}_view_{date}.png"
    if file.exists():
        os.remove(file)


def clear_sign_sign_pic(user_id: int, group_id: int):
    date = datetime.now().date()
    file = Path(SIGN_TODAY_CARD_PATH) / f"{user_id}_{group_id}_sign_{date}.png"
    if file.exists():
        os.remove(file)


def clear_sign_data_pic():
    date = datetime.now().date()
    for file in os.listdir(SIGN_TODAY_CARD_PATH):
        if str(date) not in file:
            os.remove(SIGN_TODAY_CARD_PATH / file)
