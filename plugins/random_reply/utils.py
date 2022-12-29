import re
import random
from datetime import timedelta, datetime
from nonebot import require
from models.group_member_info import GroupInfoUser
from models.sign_group_user import SignGroupUser
from .models import UserInfo
from services.db_context import db
from typing import List, Tuple
from utils.message_builder import image, record
from nonebot.adapters.onebot.v11 import Message, Bot
from typing import Union
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
    def _format_reply(cls, text: str, user: UserInfo) -> Tuple[Message, int]:
        """
        格式化 catagory == text类型 的文本内容
        返回 Message类型的消息内容(包括文本、图片、语音、at)，消息类型标识符
        flag = 0: 纯文本
        flag = 1: 文本+图片
        flag = 2: 语音+文本
        flag = 3: 语音+文本+图片
        """
        if r'[user]' in text:
            if user.level != 0:
                user_name = user.nickname if user.nickname else user.name
            else:
                user_name = "豆腐"
            text = text.replace('[user]', user_name)
        if r'[ta]' in text:
            text = text.replace('[ta]', "他" if user.gender == "male" else "她")
        if r'[at]' in text:
            text = text.replace('[at]', "")
            text = rf"[CQ:at,qq={user.qq}]" + text
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
        return Message(text), flag

    @classmethod
    async def get_final_reply_list(cls, msg: Message, user: UserInfo) -> List[Message]:
        reply_list = []
        tmp_msg = Message()
        flag = False
        for per in msg:
            if "[CQ:record" in str(per):
                reply_list.append(per)
            elif "[CQ:" not in str(per):
                if "&#91;+&#93;" in str(per):
                    per = str(per).replace("&#91;+&#93;", "")
                    await SignGroupUser.add_property(user.qq, user.group, "互动加成", max=5)
                if "&#91;-&#93;" in str(per):
                    per = str(per).replace("&#91;-&#93;", "")
                    await SignGroupUser.sub_property(user.qq, user.group, "互动加成")
                if flag:
                    reply_list.append(tmp_msg.copy())
                    tmp_msg.clear()
                if '||' in str(per):
                    tmp_text = str(per).split('||')
                    for i in tmp_text[:-1]:
                        reply_list.append(Message(i))
                    tmp_msg.append(tmp_text[-1])
                else:
                    tmp_msg.append(per)
                flag = True
            else:
                tmp_msg.append(per)
        reply_list.append(tmp_msg.copy())
        return reply_list

    @classmethod
    async def _get_reply(
            cls,
            cid: int,
            catagory: str,
            type: str,
            user: UserInfo,
    ) -> List[Tuple[Union[Message, str], int]]:
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
        for each in q:
            if not each.rule or each.rule and re.search(each.rule, user.text):
                if catagory == "text":
                    msg = each.reply
                    # 必须获取纯文本后紧接格式化再转为Message，否则Messgae会转义某些字符
                    tmp.append((msg, each.new_st))
                elif catagory == "image":
                    msg = each.reply
                    tmp.append((Message(image(msg)), each.new_st))
                else:
                    msg = each.reply
                    tmp.append((Message(record(msg)), each.new_st))
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
    ) -> Tuple[Message, int]:
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
        reply = Message()
        msg_st = 114514
        flag = 0
        user.level = -1 if isn_level else user.level
        # 找文字
        tmp = await cls._get_reply(cid, "text", type, user)
        if tmp:
            text_message = random.choice(tmp)
            msg, flag = cls._format_reply(text_message[0], user)
            msg_st = text_message[1]
            reply += msg
        # 文字回复内无图片，需要图片
        if (flag == 0 or flag == 2) and random.random() < img_rd:
            # 找图片
            tmp = await cls._get_reply(cid, "image", type, user)
            if tmp:
                image_message = random.choice(tmp)
                img = image_message[0]
                img_st = image_message[1]
                msg_st = img_st if msg_st == 114514 else msg_st
                reply += img
        # 文字回复内无语音，需要语音
        if (flag == 0 or flag == 1) and random.random() < rcd_rd:
            # 找语音
            tmp = await cls._get_reply(cid, "record", type, user)
            if tmp:
                record_message = random.choice(tmp)
                rcd = record_message[0]
                rcd_st = record_message[1]
                msg_st = rcd_st if msg_st == 114514 else msg_st
                if reply:
                    reply = rcd + reply
                else:
                    reply = rcd
        return reply, msg_st if msg_st != 114514 else 0

    @classmethod
    async def get_user_random_reply(
            cls,
            cid: int,
            catagory: str,
            type: str,
            user: UserInfo,
            isn_level: bool = False
    ) -> Tuple[Union[Message, List[Message]], int]:
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

        reply: List[Tuple[Union[Message, List[Message]], int]] = []
        # reply = []
        for each in q:
            if user.state == 0 or not each.rule or re.search(each.rule, user.text):
                msg = each.reply
                if each.catagory == "image":
                    reply.append((Message(image(msg)), each.new_st))
                elif each.catagory == "record":
                    reply.append((Message(record(msg)), each.new_st))
                else:
                    msg, flag = cls._format_reply(msg, user)
                    reply.append((msg, each.new_st))

        if reply:
            final_reply = random.choice(reply)
        else:
            final_reply = None
        if final_reply:
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
