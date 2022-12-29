import re
import os
import random
from datetime import datetime
from nonebot.adapters.onebot.v11 import Message
from models.ban_info import BanInfo
from services import logger
from utils.message_builder import image, at, poke
from utils.utils import FreqLimiter
from configs.path_config import IMAGE_PATH
from .models import UserInfo
from .utils import ReplyBank, reply_handler

_noodle_fqlmt = FreqLimiter(300, 3)
_pa_flmt = FreqLimiter(1)
_curse_flmt = FreqLimiter(5)
_poke_clmt = FreqLimiter(3, 3600)
_zwa_fqlmt = FreqLimiter(10800, 3)
_zwa_flmt = FreqLimiter(1)
zwa_func_dict = {
    "morn": [6, 7, 8, 9, 10, 11],
    "aftn": [12, 13, 14, 15, 16, 17],
    "even": [18, 19, 20, 21, 22, 23],
    "dawn": [0, 1, 2, 3, 4, 5]
}
zwa_text_dict = {
    "早": "morn",
    "上午": "morn",
    "中午": "aftn_prep",
    "下午": "aftn",
    "午": "aftn_prep",
    "睡觉": "sleep",
    "晚安": "sleep",
    "晚": "even",
    "1": "dawn_nigo",
    "25": "dawn_nigo",
    "二五": "dawn_nigo",
    "二十五": "dawn_nigo",
    "こんニーゴ": "dawn_nigo",
}


async def knd_zwa(user: UserInfo, *args, **kwargs):
    global zwa_text_dict
    global zwa_func_dict
    if _zwa_flmt.check(user.group):
        _zwa_flmt.start_cd(user.group)

        # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
        @reply_handler
        async def zwa_func(inner_user: UserInfo, cid: int):
            t = datetime.now().hour
            m = datetime.now().minute
            if m >= 50:
                t = (t + 1) % 24
            zwa_text_dict["晚"] = "dawn" if 0 <= t <= 5 else "even"
            # 得到对应当前时间段的理论回复类型
            func_type = ""
            for sw in zwa_func_dict:
                if t in zwa_func_dict[sw]:
                    func_type = sw
                    if t == 1:
                        func_type += '_nigo'
                    elif t == zwa_func_dict[sw][0]:
                        func_type += '_prep'
                    break
            # 得到用户文本所代表的实际回复类型
            text_type = ""
            for sw in zwa_text_dict:
                if sw in user.text:
                    text_type = zwa_text_dict[sw]
                    break
            # 判断两种回复类型是否一致
            if not func_type.startswith(text_type):
                if _zwa_fqlmt.count_check(inner_user.qq):
                    if text_type != "sleep":
                        _zwa_fqlmt.start_cd(inner_user.qq)
                    func_type += f"_{text_type}"
                # 多次乱打招呼，被拉黑3分钟
                else:
                    reply, state = await ReplyBank.get_user_mutil_reply(cid, "special", inner_user, 0.7, 1, True)
                    await BanInfo.ban(9, 180, user_id=inner_user.qq, group_id=inner_user.group)
                    return reply, state
            reply, state = await ReplyBank.get_user_mutil_reply(cid, func_type, inner_user, 0.7, 1, True)
            return reply, state
        return await zwa_func(user, 5, True)


async def curse_voice(user: UserInfo, *args, **kwargs):
    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    @reply_handler
    async def curse_func(inner_user: UserInfo, cid: int):
        if _curse_flmt.count_check(inner_user.qq):
            _curse_flmt.start_cd(inner_user.qq)
            # normal: 正常回复，无语类
            if random.random() < 0.7 - float(inner_user.level) * 0.05:
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "normal", inner_user, 0.5, 0.2)
            # bad: 坏回复，回应骂人类
            else:
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "bad", inner_user, 0.5, 0.2)
        else:
            # special: 骂累了
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "special", inner_user, 0.5, 0.2)
        return reply, state
    return await curse_func(user, 1)


async def eat_noodles(user: UserInfo, *args, **kwargs):
    @reply_handler
    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    async def eat_func(inner_user: UserInfo, cid: int):
        if _noodle_fqlmt.count_check(inner_user.group):
            _noodle_fqlmt.start_cd(inner_user.group)
            rd = random.random()
            if rd < 0.95:
                # normal：嗦面表情
                img, state = await ReplyBank.get_user_random_reply(cid, "image", "normal", inner_user)
                rst = img
            else:
                # special： 面洒了
                text, state = await ReplyBank.get_user_random_reply(cid, "text", "special", inner_user)
                rst = text + image("s0", "kanade/noodle")
        else:
            # 被多次(3次)请求吃面后的处理
            if random.random() <= 0.5:
                rst, state = await ReplyBank.get_user_mutil_reply(cid, "bad", inner_user, 0.5, 0.2)
            else:
                # good：嗦饱了
                rst, state = await ReplyBank.get_user_mutil_reply(cid, "good", inner_user, 0.5, 0.2)
        return rst, state
    return await eat_func(user, 4)


async def knd_kawaii(user: UserInfo, *args, **kwargs):
    # 被说不够卡瓦
    res = re.search(r"(没有?[^ ，,。.]*|不(?:怎么|比[她他我它].*)?)(?:可爱|卡瓦|kawa|kawaii|kawai|kwi|卡哇伊)", user.text)
    if res and (user.text.count("不") % 2 == 1 if "不" in user.text else True):
        reply, state = await ReplyBank.get_user_mutil_reply(3, "special", user, 0.5, 0.2)
        return reply, state

    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    @reply_handler
    async def kawa_func(inner_user: UserInfo, cid: int):
        # 不同等级概率不同
        rd_g = 0.2 + 0.04 * float(inner_user.level)
        # good:好回复，接受类
        if random.random() < rd_g and inner_user.level != 0:
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "good", user)
        # normal:通常回复，害羞类
        elif random.random() < 0.8:
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "normal", user, 0.5)
        # bad:坏回复，无表情类
        else:
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "bad", user)
        return reply, state
    return await kawa_func(user, 3)


async def my_wife(user: UserInfo, *args, **kwargs):
    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    @reply_handler
    async def wife_func(inner_user: UserInfo, cid: int):
        # 特殊处理
        if re.search(r".*(踩死?在?[我咱俺]|结婚|嫁).*", user.text):
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "other", inner_user, 1, 0.2)
            return reply, state
        if not re.search(r".*(老婆).*$", user.text):
            if re.search(r".*(爱你|爱死你|喜欢你).*", user.text):
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "other", inner_user, 1, 0.2)
                return reply, state
            return None, -1

        # special:触发特殊消息，害羞类
        if random.random() < 0.04 + float(inner_user.level) * 0.02:
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "special", inner_user, 1, 0.2)
        else:
            rd = random.random()
            # bad:触发坏消息，阴险类
            if rd < 0.6 - 0.05 * float(inner_user.level):
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "bad", inner_user, 1, 0)
            # normal:触发正常消息，无语类
            elif rd < 0.9:
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "normal", inner_user, 0.5, 0.2)
            # good:触发好消息，吃惊类
            else:
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "good", inner_user, 0.5, 0.2)
        return reply, state
    return await wife_func(user, 2)


async def poke_event(user: UserInfo, *args, **kwargs):
    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    @reply_handler
    async def poke_func(inner_user: UserInfo, cid: int):
        _poke_clmt.start_cd(inner_user.qq)
        rand = random.random()
        if not _poke_clmt.count_check(inner_user.qq):
            _poke_clmt.remove_cd(inner_user.qq)
            # 被多次(3次)骚扰后的处理
            if random.random() <= 0.15 - inner_user.level * 0.01:
                # 15%几率被拉黑
                await BanInfo.ban(9, 180, user_id=inner_user.qq, group_id=inner_user.group)
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "ban", inner_user, 0.5, 0.5)
                logger.info(f"USER {inner_user.qq} 戳了戳我,触发禁言 回复: {reply} \n")
                return reply, state
        if 0.2 < rand <= 0.5 + float(inner_user.level) * 0.01:
            # 返回文字+几率图片
            # 带图片几率
            # img_flag = True if random.random() < 0.5 else False
            # normal:疑问式回复
            if random.random() < 0.5:
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "normal", inner_user, 0.5, 0.2)
            # bad: 委婉拒绝式回复
            else:
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "bad", inner_user, 0.5, 0.2)
            logger.info(f"USER {inner_user.qq} 戳了戳我 回复: {reply} \n")
            return reply, state
        elif 0.5 + float(inner_user.level) * 0.01 < rand <= 0.8 + float(inner_user.level) * 0.02:
            # 返回纯生草图片
            img, state = await ReplyBank.get_user_random_reply(cid, "image", "special", inner_user)
            reply = img
            logger.info(f'USER {inner_user.qq} 戳了戳我 回复生草图片 \n')
            return reply, state
        else:
            # 戳对方
            logger.info(f"USER {inner_user.qq} 戳了戳我 回戳了一次 \n")
            return Message(poke(inner_user.qq)), 0
    return await poke_func(user, 6)


pjsk_chara_dict = {
    "mfy": ["mfy", "真冬", "朝比奈真冬", "mafuyu", "雪"],
    "ena": ["ena", "绘名", "东云绘名", "enana"],
    "mzk": ["mzk", "瑞希", "晓山瑞希", "mizuki", "amia"],
    "miku": ["miku", "初音", "初音未来", "白葱"],
    "rin": ["rin", "铃", "镜音铃"],
    "meiko": ["meiko"],
    "luka": ["luka", "巡音", "流歌", "巡音流歌"],
    "len": ["len", "连", "镜音连"],
    "hnm": ["hnm", "穗波", "望月穗波", "honami"],
    "mnr": ["mnr", "实乃理", "花里实乃理", "minori"],
}


async def chara_perspective(user: UserInfo, *args, **kwargs):
    global pjsk_chara_dict

    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    @reply_handler
    async def chara_func(inner_user: UserInfo, cid: int):
        for simple_name in pjsk_chara_dict:
            if user.text.lower() in pjsk_chara_dict[simple_name]:
                chara = simple_name
                reply, state = await ReplyBank.get_user_mutil_reply(cid, chara, inner_user, 1, 0.5, True)
                return reply, state
    return await chara_func(user, 8, True)


async def other_reactions(user: UserInfo, *args, **kwargs):
    # 对话装饰器，被装饰函数内只需编写单轮对话逻辑
    @reply_handler
    async def other_func(inner_user: UserInfo, cid: int):
        reply, state = await ReplyBank.get_user_mutil_reply(cid, "normal", inner_user, 0.5, 0.5)
        return reply, state
    return await other_func(user, 7)


async def pa_reg(user: UserInfo, *args, **kwargs):
    if _pa_flmt.check(user.qq):
        _pa_flmt.start_cd(user.qq)
        return Message(image("pa.jpg", "kanade"))


async def jrrp(user: UserInfo, *args, **kwargs):
    path = "kanade/jrrp"
    imgname = random.choice(os.listdir(IMAGE_PATH / path))
    return at(user.qq) + image(imgname, path)


async def knd_men(user: UserInfo, *args, **kwargs):
    reply = "圣奏宝必爱你，圣奏宝必护佑你，圣奏宝必指引你。"
    return Message(reply)


async def knd_emoji(user: UserInfo, *args, **kwargs):
    path = "kanade/original"
    imgname = random.choice(os.listdir(IMAGE_PATH / path))
    return Message(image(imgname, path))
