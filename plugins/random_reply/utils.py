import re
import random
from datetime import timedelta, datetime
from nonebot import require
from models.group_member_info import GroupInfoUser
from models.sign_group_user import SignGroupUser
from .models import UserInfo
from services.db_context import db
from typing import List, Tuple, Optional
from utils.message_builder import image, record
from nonebot.adapters.onebot.v11 import Message, Bot
from functools import wraps
try:
    import ujson as json
except ModuleNotFoundError:
    import json

require('sign_in')

from plugins.sign_in.config import lik2level


class ReplyBank(db.Model):
    __tablename__ = "reply_bank"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    rule = db.Column(db.String(), nullable=True)
    cid = db.Column(db.Integer(), nullable=False)
    now_st = db.Column(db.Integer(), nullable=False)
    new_st = db.Column(db.Integer(), nullable=False)
    level = db.Column(db.Integer(), nullable=False)
    catagory = db.Column(db.String(), nullable=False)
    type = db.Column(db.String(), nullable=False)
    reply = db.Column(db.String(), nullable=False)

    @classmethod
    async def _format_reply(cls, text: str, user: UserInfo) -> Tuple[str, int]:
        """
        格式化 catagory == text类型 的文本内容
        返回 Message类型的消息内容(包括文本、图片、语音、at)，消息类型标识符flag
        flag = 0: 纯文本
        flag = 1: 文本+图片
        flag = 2: 语音+文本
        flag = 3: 语音+文本+图片
        """
        if r'[user]' in text:
            if user.level != 0:
                user_name = user.nickname if user.nickname else user.name
                if user.level < 2 and user.level != -1:
                    user_name += '桑'
                elif user.level < 4:
                    user_name += '先生' if user.gender == 'male' else '小姐'
            else:
                user_name = "豆腐桑"
            text = text.replace('[user]', user_name)
        if r'[ta]' in text:
            text = text.replace('[ta]', "他" if user.gender == "male" else "她")
        if r'[at]' in text:
            text = text.replace('[at]', "")
            text = rf"[CQ:at,qq={user.qq}]" + text
        if "[+]" in text:
            text = text.replace("[+]", "")
            await SignGroupUser.add_property(user.qq, user.group, "互动加成", max=5)
        if "[-]" in text:
            text = text.replace("[-]", "")
            await SignGroupUser.sub_property(user.qq, user.group, "互动加成")
        flag = 0
        while True:
            if r'[image' in text:
                flag = 1
                res = re.search(r"\[image:(.*?)]", text)
                if res:
                    img_str = str(image(res.group(1)))
                    text = text.replace(rf"[image:{res.group(1)}]", img_str)
            else:
                break
        while True:
            if r'[record' in text:
                flag = 3 if flag == 1 else 2
                res = re.search(r"\[record:(.*?)]", text)
                if res:
                    rec_str = str(record(res.group(1)))
                    text = text.replace(rf"[record:{res.group(1)}]", rec_str)
            else:
                break
        return text, flag

    @classmethod
    async def get_final_reply_list(cls, msg: str) -> List[Message]:
        reply_list = []
        for per in msg.split('||'):
            reply_list.append(Message(per))
        return reply_list

    @classmethod
    async def _get_reply(
            cls,
            cid: int,
            catagory: str,
            type: str,
            user: UserInfo,
    ) -> List[Tuple[str, int]]:
        """
        获取用户对应回复内容的所有应答
        :param cid: 命令id
        :param catagory: 回复消息类型[image,text,record]
        :param type: 回复消息好坏程度[good,normal,bad,special,ex,none]
        :param user: 用户信息
        """
        tmp = []
        q = await cls.query.where(
            (cls.cid == cid) & (cls.now_st == int(user.state)) &
            (cls.catagory == catagory) & (cls.type == type) &
            (cls.level == int(user.level))
        ).gino.all()
        ft_gender = ('[F]', '[M]') if user.gender == 'male' else ('[M]', '[F]')
        for each in q:
            if (
                (not each.rule or each.rule and re.search(each.rule, user.text))
                and ft_gender[0] not in each.reply
            ):
                tmp.append((each.reply.replace(ft_gender[1], ''), each.new_st))
        return tmp

    @classmethod
    async def get_user_mutil_reply(
            cls,
            cid: int,
            type: str,
            user: UserInfo,
            img_rd: float = 1,
            rcd_rd: float = 1,
            isn_level: bool = False
    ) -> Tuple[str, int]:
        """
        获取用户最终回复的Message内容
        :param cid: 命令id
        :param catagory: 回复消息类型[image,text,record]
        :param type: 回复消息好坏程度[good,normal,bad,special,ex,none]
        :param user: 用户信息
        :param img_rd: 发图概率，默认会发图片
        :param rcd_rd: 语音概率，默认会发语音
        :param isn_level: 应答类型是否与用户等级无关
        """
        reply = ''
        msg_st = None
        flag = 0
        user.level = -1 if isn_level else user.level
        # 找文字
        tmp = await cls._get_reply(cid, "text", type, user)
        if tmp:
            text_message = random.choice(tmp)
            msg, flag = await cls._format_reply(text_message[0], user)
            msg_st = text_message[1]
            reply += msg
        # 文字回复内无图片，需要图片
        if (flag == 0 or flag == 2) and random.random() < img_rd:
            # 找图片
            tmp = await cls._get_reply(cid, "image", type, user)
            if tmp:
                image_message = random.choice(tmp)
                img = str(image(image_message[0]))
                msg_st = image_message[1] if msg_st is None else msg_st
                reply += img
        # 文字回复内无语音，需要语音
        if (flag == 0 or flag == 1) and random.random() < rcd_rd:
            # 找语音
            tmp = await cls._get_reply(cid, "record", type, user)
            if tmp:
                record_message = random.choice(tmp)
                rcd = str(record(record_message[0]))
                msg_st = record_message[1] if msg_st is None else msg_st
                reply = rcd + reply if reply else rcd
        return reply, msg_st if msg_st is not None else 0

    @classmethod
    async def get_user_random_reply(
            cls,
            cid: int,
            catagory: str,
            type: str,
            user: UserInfo,
            isn_level: bool = False
    ) -> Tuple[Optional[str], int]:
        """
        获取用户对应回复内容的随机应答
        :param cid: 命令id
        :param catagory: 回复消息类型[image,text,record]
        :param type: 回复消息好坏程度[good,normal,bad,special,ex,none]
        :param user: 用户信息
        :param isn_level: 应答类型是否与用户等级无关
        """
        user.level = -1 if isn_level else user.level
        q = await cls.query.where(
            (cls.cid == cid) & (cls.now_st == int(user.state)) &
            (cls.catagory == catagory) & (cls.type == type) &
            (cls.level == int(user.level))
        ).gino.all()

        reply: List[Tuple[str, int]] = []
        for each in q:
            if user.state == 0 or not each.rule or re.search(each.rule, user.text):
                reply.append((each.reply, each.new_st))
        final_reply = random.choice(reply) if reply else None
        if final_reply:
            if catagory == "image":
                final_reply = str(image(final_reply[0])), final_reply[1]
            elif catagory == "record":
                final_reply = str(record(final_reply[0])), final_reply[1]
            else:
                final_reply = await cls._format_reply(final_reply[0], user)[0], final_reply[1]
            return final_reply[0], final_reply[1]
        return None, -1


# none与-1搭配
# ex与多轮对话搭配
def reply_handler(f):
    @wraps(f)
    async def decorated(user: UserInfo, cid: int, isn_level: bool = False):
        # 一轮对话: 随机回复不同类型文案
        if user.state == 0:
            return await f(user, cid)
        # 多轮对话: 回复对应状态的文案
        else:
            # ex: 无关参数，回复内容具体看用户状态
            reply, state = await ReplyBank.get_user_mutil_reply(cid, "ex", user, isn_level=isn_level)
            # 得到文案，可以进行消息回复
            if reply:
                return reply, state
            # none: 无回复，特殊处理(多轮对话中得到无法处理的用户回复时的处理)
            else:
                user.state = -1  # 用户状态临时变更
                reply, state = await ReplyBank.get_user_mutil_reply(cid, "none", user, isn_level=isn_level)
                # 特殊处理得到回复：
                if reply:
                    return reply, state
                # 特殊处理得不到回复(可能是触发其他命令)
                else:
                    return None, -1

    return decorated


# 将好感度转换为好感等级
def get_level_and_next_impression(impression: float):
    if impression == 0:
        return int(lik2level[10])
    keys = list(lik2level.keys())
    for i in range(len(keys)):
        if impression > keys[i]:
            return int(lik2level[keys[i]])
    return int(lik2level[10])


async def get_user_info(bot: Bot, user: UserInfo):
    if not user.qq:
        return
    info = await bot.get_group_member_info(group_id=int(user.group), user_id=int(user.qq))
    user.name = info.get("card", "") or info.get("nickname", "")
    user.gender = info.get("sex", "")
    user.nickname = await GroupInfoUser.get_group_member_nickname(int(user.qq), int(user.group))
    user_data = await SignGroupUser.ensure(int(user.qq), int(user.group))
    if user_data.custom_level is not None and user_data.custom_level >= 0:
        user.level = user_data.custom_level
    else:
        impression = user_data.impression
        impression = impression if impression else 0
        user.level = get_level_and_next_impression(impression)
        if (
                user_data.impression_promoted_time
                and user_data.impression_promoted_time.replace(tzinfo=None) +
                timedelta(hours=8) > datetime.now()
        ):
            user.level = user.level + 1 if user.level <= len(lik2level) - 2 else user.level
        # 暂时：对于等级高达4的用户做好感限制
        user.level = 4 if user.level > 4 else user.level
