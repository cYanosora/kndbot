from typing import Dict, List, Optional
from nonebot.internal.adapter import Bot as BaseBot
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    GroupRecallNoticeEvent,
    NoticeEvent,
    FriendRecallNoticeEvent,
    GROUP,
)
from nonebot.rule import to_me
from configs.config import NICKNAME
from manager import Config
import re
from typing import Tuple, Any
from nonebot.params import CommandArg, RegexGroup
from nonebot.exception import FinishedException
from nonebot import on_command, on_regex, on_notice
from services.log import logger
from utils.message_builder import custom_forward_msg
from ._config import type2int
from ._data_source import delete_word, show_word
from ._models import WithdrawBase
from ._rule import withdraw_group_dict

__plugin_name__ = "自助撤回 [Admin]"
__plugin_type__ = "词条管理"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    简易的消息撤回机制
    可以主动撤回群内bot自身的发言(然而意义不明)
    也可以自动撤回其它成员的发言(可包含图片内容)
    (后者需要{NICKNAME}有群管理员权限)
    
    针对bot自身：
        @bot 撤回 [num1][-num2]，num 为机器人发的倒数第几条消息，从 0 开始，默认为 0
        或者直接回复需要撤回的消息，回复“撤回”二字
    针对群内普通成员：
        添加撤回词条 ?[模糊/正则] [词条内容]       :不带"关键字"三个字时，默认为需要完全匹配词条内容才会触发撤回功能
        删除撤回词条 [词条内容]                  : 直接使用词条内容删除检测词条
        删除撤回词条 id:[序号]                  : 使用指定序号删除检测词条，序号通过发送 "查看撤回词条" 获取                        
        查看撤回词条
        
    举例：
        @bot 撤回                        :撤回bot最近的一条消息
        @bot 撤回 1                      :撤回bot最近倒数第二条消息
        @bot 撤回 0-3                    :撤回bot最近的四条消息

        添加撤回词条 模糊 xxx               :当群内成员发送包含xxx的文本时，自动撤回
        添加撤回词条 正则 xxx               :当群内成员发送符合xxx正则的文本时，自动撤回(不懂什么是正则请勿使用)
        添加撤回词条 xxx                   :当群内成员发送xxx时，自动撤回
        删除撤回词条 xxx                   :不再撤回内容为xxx的消息(无论是关键字类型还是全匹配类型)
        删除撤回词条 id:0                  :不再撤回序号为0所指代的词条内容
""".strip()
__plugin_settings__ = {
    "admin_level": 6,
    "cmd": ["撤回", "自助撤回"],
}
__plugin_configs__ = {
    "withdraw_max_size": {
        "value": 100,
        "help": "能够撤回的最久远消息数量",
        "default_value": 100
    }
}


msg_ids: Dict[str, List[int]] = {}
max_size = Config.get_config("withdraw", "withdraw_max_size", 100)


def get_key(msg_type: str, id: int):
    return f"{msg_type}_{id}"


async def save_msg_id(
    bot: BaseBot, e: Optional[Exception],
    api: str, data: Dict[str, Any], result: Any
):
    global msg_ids
    try:
        if api == "send_msg":
            msg_type = data["message_type"]
            id = data["group_id"] if msg_type == "group" else data["user_id"]
        elif api == "send_private_msg":
            msg_type = "private"
            id = data["user_id"]
        elif api == "send_group_msg":
            msg_type = "group"
            id = data["group_id"]
        else:
            return
        key = get_key(msg_type, id)
        msg_id = int(result["message_id"])

        if key not in msg_ids:
            msg_ids[key] = []
        msg_ids[key].append(msg_id)
        if len(msg_ids) > max_size:
            msg_ids[key].pop(0)
    except:
        pass


Bot.on_called_api(save_msg_id)

withdraw = on_command(
    "撤回",
    permission=GROUP,
    priority=5,
    block=True,
    rule=to_me()
)


@withdraw.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent):
        msg_type = "group"
        id = event.group_id
    else:
        msg_type = "private"
        id = event.user_id
    key = get_key(msg_type, id)
    # 如果有回复，直接处理
    try:
        if event.reply:
            msg_id = event.reply.message_id
            try:
                await bot.delete_msg(message_id=msg_id)
                logger.info(f"{msg_type.upper()} USER{event.get_user_id}撤回了{NICKNAME}的消息")
                return
            except:
                await withdraw.finish("撤回失败，可能已超时")
    except:
        pass

    def extract_num(text: str) -> Tuple[int, int]:
        if not text:
            return 0, 1

        if text.isdigit() and 0 <= int(text) < len(msg_ids[key]):
            return int(text), int(text) + 1

        nums = text.split("-")[:2]
        nums = [n.strip() for n in nums]
        if len(nums) == 2 and nums[0].isdigit() and nums[1].isdigit():
            start_num = int(nums[0])
            end_num = min(int(nums[1]), len(msg_ids[key]))
            if end_num > start_num:
                return start_num, end_num
        return 0, 1

    text = msg.extract_plain_text().strip()
    start_num, end_num = extract_num(text)

    res = ""
    message_ids = [msg_ids[key][-num - 1] for num in range(start_num, end_num)]
    for message_id in message_ids:
        try:
            await bot.delete_msg(message_id=message_id)
            msg_ids[key].remove(message_id)
        except:
            if not res:
                res = "撤回失败，可能已超时"
                if end_num - start_num > 1:
                    res = "部分消息" + res
            continue
    if res:
        await withdraw.finish(res)
        logger.info(f"{msg_type.upper()} USER{event.get_user_id}撤回了{NICKNAME}的消息")
        return


# bot消息撤回通知
async def _group_recall(bot: Bot, event: NoticeEvent) -> bool:
    if isinstance(event, GroupRecallNoticeEvent) or isinstance(event, FriendRecallNoticeEvent):
        return str(event.user_id) == str(bot.self_id)
    else:
        return False


withdraw_notice = on_notice(_group_recall)


@withdraw_notice.handle()
async def _(event: NoticeEvent):
    if isinstance(event, GroupRecallNoticeEvent):
        type = "group"
    else:
        type = "private"
    msg_id = event.message_id
    id = event.group_id
    key = get_key(type, id)
    if key in msg_ids and msg_id in msg_ids[key]:
        msg_ids[key].remove(msg_id)


# 以下为自助撤回群员消息功能

add_entry = on_regex(r"^添加撤回词条\s*(精准|模糊|正则)?(.*)", priority=3, block=True)
delete_word_matcher = on_command("删除撤回词条", aliases={'取消撤回词条'}, priority=3, block=True)
show_word_matcher = on_command("显示撤回词条", aliases={"查看撤回词条"}, priority=3, block=True)


@add_entry.handle()
async def _(
        event: GroupMessageEvent,
        reg_group: Tuple[Any, ...] = RegexGroup(),
):
    # 私聊、全局只允许超管使用
    word_type, entry = reg_group
    word_type = type2int.get(word_type, 0)
    # 检测词条完整性
    if not entry.strip():
        await add_entry.finish("检测词条不能为空")
    try:
        # 对正则问题额外配置
        if word_type == 2:
            try:
                re.compile(entry)
            except re.error:
                await add_entry.finish(f"添加词条失败，正则表达式 {entry} 非法！")
        await WithdrawBase.add_entry_answer(
            event.user_id,
            event.group_id,
            word_type,
            entry,
        )
    except Exception as e:
        if isinstance(e, FinishedException):
            await add_entry.finish()
        logger.error(
            f"(USER {event.user_id}, GROUP {event.group_id})"
            f" 添加词条 {entry} 发生错误 {type(e)}: {e} "
        )
        await add_entry.finish(f"添加词条 {entry} 发生错误！")
    await add_entry.send("添加词条 " + Message(entry) + " 成功！")
    if not withdraw_group_dict.get(str(event.self_id)):
        withdraw_group_dict[str(event.self_id)] = []
    if event.group_id not in withdraw_group_dict[str(event.self_id)]:
        withdraw_group_dict[str(event.self_id)].append(event.group_id)
    logger.info(
        f"(USER {event.user_id}, GROUP "
        f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
        f" 添加词条 {entry} 成功！"
    )


@delete_word_matcher.handle()
async def _(
        event: GroupMessageEvent,
        arg: Message = CommandArg()
):
    if not (msg := arg.extract_plain_text().strip()):
        await delete_word_matcher.finish(
            "此命令之后需要跟随指定词条，通过“显示撤回词条“查看\n"
            "注：设置的检测词条中含有图片、艾特、qq黄豆表情时只能使用问题的下标删除"
        )
    result = await delete_word(msg, event.group_id)
    await delete_word_matcher.send(result)
    logger.info(
        f"(USER {event.user_id}, GROUP {event.group_id})" +
        f" 删除词条:" + msg
    )
    if not await WithdrawBase.exist_any_entry(event.group_id):
        if withdraw_group_dict.get(str(event.self_id)):
            withdraw_group_dict[str(event.self_id)].remove(event.group_id)


@show_word_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    # 显示群聊全部撤回词条
    msg_list = await show_word(event.group_id)
    # 处理无词条的一些情况
    if isinstance(msg_list, str):
        await show_word_matcher.finish(msg_list)
    # 使用合并转发返回词条结果
    else:
        await bot.send_group_forward_msg(
            group_id=event.group_id, messages=custom_forward_msg(msg_list, bot.self_id)
        )
        logger.info(
            f"(USER {event.user_id}, GROUP {event.group_id})"
            f" 查看群撤回词条"
        )
