from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, GROUP
from nonebot import on_command
from nonebot.rule import to_me
from models.group_member_info import GroupInfoUser
from models.ban_info import BanInfo
from services.log import logger
from configs.config import NICKNAME
from manager import Config
from nonebot.params import CommandArg
from utils.message_builder import image
import random

__plugin_name__ = "昵称系统"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    个人昵称系统，使用违禁昵称会被bot短暂拉黑作为惩罚()
    指令：
        @bot 以后叫我 [昵称]
        @bot 我是谁/我叫什么
        取消昵称
""".strip()
__plugin_settings__ = {
    "cmd": ["昵称系统"],
}
__plugin_configs__ = {
    "BLACK_WORD": {
        "value": [
            "爸", "爹", "爷", "妈", "死",
            "老婆", "老公", "宝贝", "丈夫",
            "歌姬", "寄", "鸡", "傻", "啥比"
        ],
        "help": "昵称所屏蔽的关键词，会被替换为 *",
        "default_value": None
    }
}

nickname = on_command(
    "以后叫我",
    aliases={"以后请叫我", "称呼我", "以后请称呼我", "以后称呼我", "叫我", "请叫我"},
    rule=to_me(),
    permission=GROUP,
    priority=3,
    block=True,
)

my_nickname = on_command(
    "我的昵称",
    aliases={"我叫什么", "我是谁", "我的名字"},
    rule=to_me(),
    permission=GROUP,
    priority=3,
    block=True
)

cancel_nickname = on_command("取消昵称", priority=3, permission=GROUP,  block=True)


@nickname.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await nickname.finish("嗯？你没名字吗？", at_sender=True)
    if len(msg) > 10:
        await nickname.finish("昵称太长了..叫起来好累...", at_sender=True)
    if msg in bot.config.superusers:
        await nickname.finish(f"笨蛋！不许和{NICKNAME}的bot主同名！", at_sender=True)
    if msg in bot.config.nickname:
        await nickname.finish(f"诶？我的名字要被夺走了嘛..", at_sender=True)
    black_word = Config.get_config("nickname", "BLACK_WORD", [])
    for i in black_word:
        msg = msg.replace(i, "*"*len(i))
    # 昵称全是违禁词，作特殊处理
    if msg == "*" * len(msg):
        reply = random.choice(["为什么想出这样的称呼...=n=", "这种称呼是不是有点..."])
        # 50%带图片
        reply += image("liuhan", "kanade") if random.random() < 0.5 else ""
        # ban用户
        await BanInfo.ban(9, 60, event.user_id, event.group_id)
        await nickname.finish(Message(reply))
    if await GroupInfoUser.set_group_member_nickname(event.user_id, event.group_id, msg):
        if len(msg) < 5:
            if random.random() < 0.3:
                msg = "~".join(msg)
        await nickname.send(
            random.choice(
                [
                    f"知道啦，{msg}，以后就这么叫你吧",
                    f"嗯嗯，{NICKNAME}记住你的昵称了哦，{msg}",
                    f"诶，突然要叫你昵称什么的...{msg}..",
                    f"{NICKNAME}会好好记住{msg}的，放心吧",
                    f"好的..那以后就叫你{msg}了.",
                ]
            ),
            at_sender=True
        )
        logger.info(f"USER {event.user_id} GROUP {event.group_id} 设置群昵称 {msg} 成功")
    else:
        await nickname.send("设置昵称失败，请更新群组成员列表后再次尝试。", at_sender=True)
        logger.warning(f"USER {event.user_id} GROUP {event.group_id} 设置群昵称 {msg} 失败")


@my_nickname.handle()
async def _(event: GroupMessageEvent):
    try:
        nickname_ = await GroupInfoUser.get_group_member_nickname(event.user_id, event.group_id)
    except AttributeError:
        nickname_ = ""
    if nickname_:
        await my_nickname.send(
            random.choice(
                [
                    f"姑且还是记得你的，是叫{nickname_}对吧",
                    f"没有忘记你哟，{nickname_}",
                    f"那个..{NICKNAME}记得你应该是{nickname_}来着",
                    f"哎？{nickname_}..怎么了吗..突然这样问..",
                ]
            ),
            at_sender=True
        )
    else:
        nickname_ = event.sender.card or event.sender.nickname
        await my_nickname.send(
            random.choice(
                [
                    "没..没有昵称嘛，{}桑",
                    "是{}桑啊，有什么事吗？",
                    "你是{}桑对吧？"
                ]
            ).format(nickname_),
            at_sender=True
        )


@cancel_nickname.handle()
async def _(event: GroupMessageEvent):
    nickname_ = await GroupInfoUser.get_group_member_nickname(
        event.user_id, event.group_id
    )
    if nickname_:
        await cancel_nickname.send(f"知道了，{nickname_}桑。啊...已经不叫这个了(◞‸◟ )", at_sender=True)
        await GroupInfoUser.set_group_member_nickname(event.user_id, event.group_id, "")
    else:
        await cancel_nickname.send("...你还没有昵称啊", at_sender=True)

