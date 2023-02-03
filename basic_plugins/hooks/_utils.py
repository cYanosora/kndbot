from nonebot.adapters.onebot.v11 import MessageEvent, ActionFailed, GroupMessageEvent, Bot, Message
from manager import Config
from models.friend_user import FriendUser
from models.group_member_info import GroupInfoUser
from utils.message_builder import at
from utils.utils import FreqLimiter


# 管理员权限不足通知cd
_flmt = FreqLimiter(Config.get_config("hook", "CHECK_NOTICE_INFO_CD"))
# 群权限不足通知cd
_flmt_g = FreqLimiter(Config.get_config("hook", "CHECK_NOTICE_INFO_CD"))
# 超管关闭功能通知cd
_flmt_s = FreqLimiter(Config.get_config("hook", "CHECK_NOTICE_INFO_CD"))
# 功能维护通知cd
_flmt_c = FreqLimiter(Config.get_config("hook", "CHECK_NOTICE_INFO_CD"))
# 禁言通知cd
_flmt_b = FreqLimiter(Config.get_config("hook", "CHECK_NOTICE_INFO_CD"))

# 以下插件触发时默认不计数
oppose_cd_modules = oppose_count_modules = [
    "petpet", "send_image", "miragetank", "pix", "pixiv_rank_search", "youthstudy", 'guess'
]
# 以下插件私聊中可用
ignore_module = [
    "dialogue",  # 联系管理员
    "invite_manager"  # 邀请入群
]


async def send_msg(rst: str, bot: Bot, event: MessageEvent):
    """
    格式化发送信息
    :param rst: pass
    :param bot: pass
    :param event: pass
    """
    rst = await init_rst(rst, event)
    try:
        if isinstance(event, GroupMessageEvent):
            await bot.send_group_msg(group_id=event.group_id, message=Message(rst))
        else:
            await bot.send_private_msg(user_id=event.user_id, message=Message(rst))
    except ActionFailed:
        pass


async def init_rst(rst: str, event: MessageEvent):
    if "[uname]" in rst:
        uname = event.sender.card or event.sender.nickname
        rst = rst.replace("[uname]", uname)
    if "[nickname]" in rst:
        try:
            if isinstance(event, GroupMessageEvent):
                nickname = await GroupInfoUser.get_group_member_nickname(
                    event.user_id, event.group_id
                )
            else:
                nickname = await FriendUser.get_friend_nickname(event.user_id)
        except:
            nickname = "你"
        rst = rst.replace("[nickname]", nickname)
    if "[at]" in rst:
        if isinstance(event, GroupMessageEvent):
            rst = rst.replace("[at]", str(at(event.user_id)))
        else:
            rst = rst.replace("[at]", "")
    return rst
