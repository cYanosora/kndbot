from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, GroupMessageEvent
from nonebot.permission import SUPERUSER
from configs.config import NICKNAME
from utils.utils import is_number, get_message_img
from utils.message_builder import image
from utils.message_builder import text as _text
from services.log import logger
from utils.message_builder import at
from nonebot.params import CommandArg


__plugin_name__ = "联系管理员"
__plugin_type__ = "其他"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    有什么话想对bot管理员说嘛？
    指令：
        联系管理/滴滴滴 ?[文本] ?[图片]
    示例：
        滴滴滴 在？出来处理个bug？
    提示：
        若只是不懂如何触发bot功能，别急着问master，
        请先仔细阅读bot使用方法(发送：@bot help)
        其他问题只要是关于bot的就都可以问
""".strip()
__plugin_superuser_usage__ = """
superuser usage：
    管理员对消息的回复
    指令：
        /t                      : 查看当前存储的消息id
        /t -d [id]              : 删除指定id的对话
        /t -d                   : 删除所有回复消息
        /t [qq] [文本]           : 私聊用户
        /t -1   [group] [文本]   : 在group内发送消息
        /t [qq] [group] [文本]   : 在group内回复指定用户
        /t [id] [文本]           : 回复指定id的对话
""".strip()
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["滴滴滴", "联系管理员", "联系管理"],
}

dialogue_data = {}
dialogue = on_command("联系管理员", aliases={"滴滴滴", "联系管理"}, priority=5, block=True)
reply = on_command("/t", aliases={".t"}, priority=1, permission=SUPERUSER, block=True)


@dialogue.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    text = arg.extract_plain_text().strip()
    img_msg = _text("")
    for img in get_message_img(event.json()):
        img_msg += image(img)
    if not text and not img_msg:
        await dialogue.send("请发送 滴滴滴 + 您要说的内容~", at_sender=True)
    else:
        group_id = 0
        group_name = "None"
        nickname = event.sender.nickname
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            group_name = (await bot.get_group_info(group_id=event.group_id))["group_name"]
            nickname = event.sender.card or event.sender.nickname
        for coffee in bot.config.superusers:
            await bot.send_private_msg(
                user_id=int(coffee),
                message=_text(
                    f"*****一份交流报告*****\n"
                    f"昵称：{nickname}({event.user_id})\n"
                    f"群聊：{group_name}({group_id})\n"
                    f"消息：{text}"
                )
                + img_msg,
            )
        await dialogue.send(_text(f"消息已发送至管理员，请耐心等候回复"), at_sender=True)
        nickname = event.sender.nickname if event.sender.nickname else event.sender.card
        dialogue_data[len(dialogue_data)] = {
            "nickname": nickname,
            "user_id": event.user_id,
            "group_id": group_id,
            "group_name": group_name,
            "msg": _text(text) + img_msg,
        }
        logger.info(f"Q{event.user_id}@群{group_id} 联系管理员：text:{text}")


@reply.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    img_msg = _text("")
    for img in get_message_img(event.json()):
        img_msg += image(img)
    if not msg and not img_msg:
        result = "*****待回复消息总览*****\n"
        for key in dialogue_data.keys():
            result += (
                f"id：{key}\n"
                f'\t昵称：{dialogue_data[key]["nickname"]}({dialogue_data[key]["user_id"]})\n'
                f'\t群名：{dialogue_data[key]["group_name"]}({dialogue_data[key]["group_id"]})\n'
                f'\t消息：{dialogue_data[key]["msg"]}'
                f"\n--------------------\n"
            )
        await reply.finish(Message(result[:-1]))
    msg = msg.split()
    text = ""
    group_id = 0
    user_id = -1
    if msg[0] == "-d":
        if len(msg) == 2:
            id_ = int(msg[1])
            try:
                dialogue_data.pop(id_)
                await reply.finish(f"清空回复消息(id:{id_})成功")
            except:
                await reply.finish(f"清空回复消息失败，可能是没有此id的消息")
        else:
            dialogue_data.clear()
            await reply.finish("清空回复消息成功")
    if is_number(msg[0]):
        if len(msg[0]) < 3:
            msg[0] = int(msg[0])
            if msg[0] >= 0:
                try:
                    id_ = msg[0]
                    user_id = dialogue_data[id_]["user_id"]
                    group_id = dialogue_data[id_]["group_id"]
                    text = " ".join(msg[1:])
                    dialogue_data.pop(id_)
                except:
                    await reply.finish(f"回复消息失败，可能是没有此id的消息")
            else:
                user_id = 0
                if is_number(msg[1]):
                    group_id = int(msg[1])
                    text = " ".join(msg[2:])
                else:
                    await reply.finish("群号错误", at_sender=True)
        else:
            user_id = int(msg[0])
            if is_number(msg[1]) and len(msg[1]) > 5:
                group_id = int(msg[1])
                text = " ".join(msg[2:])
            else:
                group_id = 0
                text = " ".join(msg[1:])
    else:
        await reply.finish("第一参数，请输入qq号或消息id", at_sender=True)
    text += img_msg
    if group_id:
        if user_id:
            await bot.send_group_msg(
                group_id=group_id, message="*****管理员回复*****\n"+at(user_id)+text
            )
        else:
            await bot.send_group_msg(group_id=group_id, message="*****管理员回复*****\n"+text)
        await reply.finish("群聊消息发送成功", at_sender=True)
    else:
        if user_id in [qq["user_id"] for qq in await bot.get_friend_list()]:
            await bot.send_private_msg(
                user_id=user_id, message="*****管理员回复*****\n"+text
            )
            await reply.finish("私聊消息发送成功", at_sender=True)
        else:
            await reply.send(f"对方并不是{NICKNAME}的好友。", at_sender=True)
