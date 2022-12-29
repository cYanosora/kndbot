import re
import shlex
from io import BytesIO
from typing import List, Optional
from nonebot.rule import Rule
from nonebot import get_driver
from nonebot.typing import T_State
from nonebot.params import Depends
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageSegment,
    MessageEvent,
    GroupMessageEvent,
    unescape,
)

from utils.imageutils import BuildImage

from .utils import UserInfo
from .download import download_url, download_avatar


USERS_KEY = "USERS"
SENDER_KEY = "SENDER"
ARGS_KEY = "ARGS"
REGEX_DICT = "REGEX_DICT"
REGEX_ARG = "REGEX_ARG"


def regex(pattern: str, arg_type: str = "NoArg") -> Rule:
    def checker(event: MessageEvent, state: T_State) -> bool:
        msg = event.get_message()
        msg_seg: MessageSegment = msg[0]
        if not msg_seg.is_text():
            return False

        seg_text = str(msg_seg).lstrip()
        start = "|".join(get_driver().config.command_start)
        matched = re.match(rf"(?:{start})(?:{pattern})", seg_text, re.IGNORECASE)
        if not matched:
            return False

        new_msg = msg.copy()
        seg_text = seg_text[matched.end():].lstrip()
        if seg_text:
            new_msg[0].data["text"] = seg_text
        else:
            new_msg.pop(0)
        state[REGEX_DICT] = matched.groupdict()
        state[REGEX_ARG] = new_msg
        trigger_msg = str(new_msg)
        if event.reply:
            # print(event.reply.json())
            if event.reply.message.get("image"):
                trigger_msg = trigger_msg + f"[CQ:at,qq={event.reply.sender.user_id}]"
        if event.is_tome():
            trigger_msg = trigger_msg + f"[CQ:at,qq={event.self_id}]"
        # print('trigger_msg',trigger_msg)
        # print('arg_type == "NoArg"',arg_type == "NoArg")
        # print('not trigger_msg == "自己"',not trigger_msg == "自己")
        # print('not is_qq(trigger_msg)',not is_qq(trigger_msg))
        # print('not trigger_msg.startswith("[CQ:")',not trigger_msg.startswith("[CQ:"))
        if(
            arg_type == "NoArg"
            and not trigger_msg == "自己"
            and not is_qq(trigger_msg)
            and not trigger_msg.startswith("[CQ:")
        ):
            return False
        else:
            return True

    return Rule(checker)


def is_qq(msg: str):
    return msg.isdigit() and 11 >= len(msg) >= 5


def split_msg():
    def dependency(event: MessageEvent, state: T_State):
        def _is_at_me_seg(segment: MessageSegment):
            return segment.type == "at" and str(segment.data.get("qq", "")) == str(
                event.self_id
            )

        msg: Message = state["REGEX_ARG"]

        if event.to_me:
            raw_msg = Message(event.raw_message)
            i = -1
            last_msg_seg = raw_msg[i]
            if (
                last_msg_seg.type == "text"
                and not last_msg_seg.data["text"].strip()
                and len(raw_msg) >= 2
            ):
                i -= 1
                last_msg_seg = raw_msg[i]
            if _is_at_me_seg(last_msg_seg):
                msg.append(last_msg_seg)

        users: List[UserInfo] = []
        args: List[str] = []

        if event.reply:
            for img in event.reply.message["image"]:
                users.append(UserInfo(img_url=str(img.data.get("url", ""))))

        for msg_seg in msg:
            if msg_seg.type == "at":
                users.append(
                    UserInfo(
                        qq=str(msg_seg.data.get("qq", "")),
                        group=str(event.group_id)
                        if isinstance(event, GroupMessageEvent)
                        else "",
                    )
                )
            elif msg_seg.type == "image":
                users.append(UserInfo(img_url=str(msg_seg.data.get("url", ""))))
            elif msg_seg.type == "text":
                raw_text = str(msg_seg)
                try:
                    texts = shlex.split(raw_text)
                except:
                    texts = raw_text.split()
                for text in texts:
                    if is_qq(text):
                        users.append(UserInfo(qq=text))
                    elif text == "自己":
                        users.append(
                            UserInfo(
                                qq=str(event.user_id),
                                group=str(event.group_id)
                                if isinstance(event, GroupMessageEvent)
                                else "",
                            )
                        )
                    else:
                        text = unescape(text).strip()
                        if text:
                            args.append(text)

        if not users and event.is_tome():
            users.append(UserInfo(qq=str(event.self_id), group=str(event.group_id)))

        sender = UserInfo(qq=str(event.user_id))
        state[SENDER_KEY] = sender
        state[USERS_KEY] = users
        state[ARGS_KEY] = args

    return Depends(dependency)


async def get_user_info(bot: Bot, user: UserInfo):
    if not user.qq:
        return

    if user.group:
        info = await bot.get_group_member_info(
            group_id=int(user.group), user_id=int(user.qq)
        )
        user.name = info.get("card", "") or info.get("nickname", "")
        user.gender = info.get("sex", "")
    else:
        info = await bot.get_stranger_info(user_id=int(user.qq))
        user.name = info.get("nickname", "")
        user.gender = info.get("sex", "")


async def download_image(user: UserInfo):
    img = None
    if user.qq:
        img = await download_avatar(user.qq)
    elif user.img_url:
        img = await download_url(user.img_url)

    if img:
        user.img = BuildImage.open(BytesIO(img))


def Users(min_num: int = 1, max_num: int = 1):
    async def dependency(bot: Bot, state: T_State):
        users: List[UserInfo] = state[USERS_KEY]
        if len(users) > max_num or len(users) < min_num:
            return

        for user in users:
            await get_user_info(bot, user)
            await download_image(user)
        return users

    return Depends(dependency)


def User():
    async def dependency(users: Optional[List[UserInfo]] = Users()):
        if users:
            return users[0]

    return Depends(dependency)


def UserImgs(min_num: int = 1, max_num: int = 1):
    async def dependency(state: T_State):
        users: List[UserInfo] = state[USERS_KEY]
        if len(users) > max_num or len(users) < min_num:
            return

        for user in users:
            await download_image(user)
        return [user.img for user in users]

    return Depends(dependency)


def UserImg():
    async def dependency(imgs: List[BuildImage] = UserImgs()):
        if imgs:
            return imgs[0]

    return Depends(dependency)


def Sender():
    async def dependency(bot: Bot, state: T_State):
        sender: UserInfo = state[SENDER_KEY]
        await get_user_info(bot, sender)
        await download_image(sender)
        return sender

    return Depends(dependency)


def SenderImg():
    async def dependency(state: T_State):
        sender: UserInfo = state[SENDER_KEY]
        await download_image(sender)
        return sender.img

    return Depends(dependency)


def Args(min_num: int = 1, max_num: int = 1):
    async def dependency(state: T_State):
        args: List[str] = state[ARGS_KEY]
        if len(args) > max_num or len(args) < min_num:
            return
        return args

    return Depends(dependency)


def RegexArg(key: str):
    async def dependency(state: T_State):
        arg: dict = state[REGEX_DICT]
        return arg.get(key, None)

    return Depends(dependency)


def Arg(possible_values: List[str] = []):
    async def dependency(args: List[str] = Args(0, 1)):
        if args:
            arg = args[0]
            if possible_values and arg not in possible_values:
                return
            return arg
        else:
            return ""

    return Depends(dependency)


def NoArg():
    async def dependency(args: List[str] = Args(0, 0)):
        return

    return Depends(dependency)
