from typing import Tuple
from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot, Message, MessageEvent, MessageSegment, PrivateMessageEvent
)
from nonebot.params import CommandArg, Matcher, Command
from services import logger
from utils.limit_utils import access_cd, access_count
from .config import (
    config, need_at,
    poe_matcher_params, bing_matcher_params, gpt_matcher_params
)
from .utils import (
    handle_msg, get_session_owner,
    get_avail_reply_modes, get_avail_models,
    checker_super, checker_admin, ask
)
from .poe import poe_session_data
from .bing import bing_session_data
from .chatgpt import gpt_session_data

__plugin_name__ = "GPT"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    使用 OpenAI的ChatGPT 或者 Poe的GPT服务 或者 微软必应的EdgeGPT 进行沟通
    因服务器性能有限，仅在特定群开放
    指令：
        chat/Chat/CHAT [文本]                ： 请求ChatGPT的回复
        bing/Bing/BING [文本]                ： 请求BingGPT的回复
        poe/Poe/POE [文本]                   ： 请求PoeGPT的回复
        
        # 对于ChatGPT有以下额外指令
        重置gpt对话/会话                     ： 重置会话记录，开始新的对话，仅群管可用
        刷新gpt对话/会话                     ： 同上，仅群管可用
        
        当前gpt人格                         ：查看当前人格设定
        设置gpt人格 [人格]                   ：设置当前人格，仅群管可用，需要具有一定话术水平才能催眠chatgpt
        重置gpt人格                         ：重置人格为默认chatgpt人格，仅群管可用
        
        # 对于Poe有以下额外指令
        当前poe模型                         ：查看当前模型设定
        设置poe模型 [模型]                   ：设置当前模型，仅群管可用，仅支持已存在的可选模型，不可以自定义
        重置poe模型                         ：重置模型为默认，仅群管可用

        当前poe人格                         ：查看当前人格设定
        设置poe人格 [人格]                   ：设置当前人格，仅群管可用，需要具有一定话术水平才能催眠gpt
        重置poe人格                         ：重置人格为默认，仅群管可用

        # 对于Bing有以下额外指令
        设置应答模式                      ：设置微软Bing的GPT回复模式 
""".strip()
__plugin_settings__ = {
    "level": 6,
    "cmd": ['GPT', 'gpt']
}
__plugin_count_limit__ = {
    "max_count": 200,
    "limit_type": "user",
    "rst": "你今天已经使用了[count]次啦，已经足够了吧[at]",
}
__plugin_cd_limit__ = {
    "cd": 60,
    "limit_type": "group",
    "count_limit": 3,
    "rst": "别急，[cd]s后再用！"
}


# Poe
## 模型
current_model = on_command("当前poe模型", priority=5, block=True, **need_at)
set_model = on_command("设置poe模型", aliases={"poe模型设置"}, priority=5, block=True, **need_at)
reset_model = on_command("重置poe模型", aliases={"刷新poe模型"}, priority=5, block=True, **need_at)
## 人格
current_preset = on_command("当前poe人格", aliases={"查看poe人格", "当前gpt人格", "查看gpt人格"}, priority=5, block=True, **need_at)
set_preset = on_command("设置poe人格", aliases={"poe人格设置", "gpt人格设置", "设置gpt人格"}, priority=5, block=True, **need_at)
reset_preset = on_command("重置poe人格", aliases={"刷新poe人格",  "刷新gpt人格", "重置poe人格"}, priority=5, block=True, **need_at)
## 聊天
poechat = on_command(priority=4, block=True, **poe_matcher_params)

# Bing
## 模型
set_reply_mode = on_command("设置应答模式", priority=5, block=True, **need_at)
bingchat = on_command(priority=4, block=True, **bing_matcher_params)

# ChatGPT
## 会话
refresh_chat = on_command("重置gpt会话", aliases={"重置gpt对话", "刷新gpt对话", "刷新gpt会话"}, priority=5, block=True, **need_at)
gptchat = on_command(priority=4, block=True, **gpt_matcher_params)


@current_model.handle()
async def _(matcher: Matcher, event: MessageEvent):
    session_owner = get_session_owner(event)
    model = poe_session_data.get_model(session_owner)
    await matcher.finish(f"当前的模型：{model}")


@set_model.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if not await checker_admin(event, bot):
        await matcher.finish("仅管理员可以设置模型")
    # 参数解析
    target_id = None
    model = arg.extract_plain_text().strip()
    if checker_super(event, bot):
        obj = model.split()
        if len(obj) > 1:
            if obj[0].isdigit():
                target_id = obj[0]
            else:
                await matcher.finish("设定目标必须为群号/QQ号")
            model = ' '.join(obj[1:])
        elif len(obj) == 1:
            model = obj[0]
    avail_models = get_avail_models()
    if not model:
        await matcher.finish("设定的模型不能为空！\n当前可用的模型有" + ','.join(avail_models))
    for each_model in avail_models:
        if each_model.lower() == model:
            model = each_model
            break
    else:
        await matcher.finish("设定的模型不存在！\n当前可用的模型有" + ','.join(avail_models))
        return
    session_owner = get_session_owner(event, target_id)
    poe_session_data.set_model(session_owner, model)
    logger.info(
        f"User {event.user_id}\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"设置poe模型: {model}"
    )
    await matcher.finish(f"你设定的新模型为：{model}")


@reset_model.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if not await checker_admin(event, bot):
        await matcher.finish("仅管理员可以重置模型")
    obj = ''
    if checker_super(event, bot):
        obj = arg.extract_plain_text().strip()
        if not obj.isdigit():
            obj = ''
    session_owner = get_session_owner(event, obj)
    poe_session_data.set_model(session_owner, config.poe_default_model)
    logger.info(
        f"User {event.user_id} "
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'} "
        f"重置poe模型"
    )
    await matcher.finish("模型已重置")


@current_preset.handle()
async def _(matcher: Matcher, event: MessageEvent, cmd: Tuple[str, ...] = Command()):
    session_owner = get_session_owner(event)
    if 'poe' in cmd[0]:
        cmd = 'poe'
        preset = poe_session_data.get_preset(session_owner)
    else:
        cmd = 'gpt'
        preset = gpt_session_data.get_preset(session_owner)
    if not preset:
        await matcher.finish(f"当前还没有设定的{cmd}人格哦")
    else:
        await matcher.finish(f"当前的{cmd}人格：{preset}")


@set_preset.handle()
async def _(
    matcher: Matcher, event: MessageEvent, bot: Bot,
    cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()
):
    if not await checker_admin(event, bot):
        await matcher.finish("仅管理员可以设置模型")
    # 参数解析
    target_id = None
    preset = arg.extract_plain_text().strip()
    if checker_super(event, bot):
        obj = preset.split()
        if len(obj) > 1:
            if obj[0].isdigit():
                target_id = obj[0]
            else:
                await matcher.finish("设定目标必须为群号/QQ号")
            preset = ' '.join(obj[1:])
        elif len(obj) == 1:
            preset = obj[0]
    if not preset:
        await matcher.finish("设定的人格不能为空！")
    session_owner = get_session_owner(event, target_id)
    if 'poe' in cmd[0]:
        cmd = 'poe'
        poe_session_data.set_preset(session_owner, preset)
    else:
        cmd = 'gpt'
        gpt_session_data.set_preset(session_owner, preset)
    logger.info(
        f"User {event.user_id}\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"设置{cmd}人格: {preset}"
    )
    await matcher.finish(f"你设定的{cmd}新人格为：{preset}")


@reset_preset.handle()
async def _(
    matcher: Matcher, event: MessageEvent, bot: Bot,
    cmd: Tuple[str, ...] = Command(), arg: Message = CommandArg()
):
    if not await checker_admin(event, bot):
        await matcher.finish("目前为群聊会话模式，仅管理员可以重置人格")
    obj = ''
    if checker_super(event, bot):
        obj = arg.extract_plain_text().strip()
        if not obj.isdigit():
            obj = ''
    session_owner = get_session_owner(event, obj)
    if 'poe' in cmd[0]:
        cmd = 'poe'
        poe_session_data.set_preset(session_owner, config.poe_default_preset)
    else:
        cmd = 'gpt'
        gpt_session_data.set_preset(session_owner, config.gpt_default_preset)
    logger.info(
        f"User {event.user_id} "
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'} "
        f"重置{cmd}人格"
    )
    await matcher.finish(f"{cmd}人格已重置")


@poechat.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await matcher.finish("你问了什么嘛？", at_sender=True)
    session_owner = get_session_owner(event)
    text = await ask('poe', session_owner, msg)
    if text is None:
        await matcher.finish("消息太快了，请稍后再试！", at_sender=True)
    reply = await handle_msg(text)
    if isinstance(event, PrivateMessageEvent):
        await matcher.send(reply)
    else:
        await matcher.send(MessageSegment.reply(event.message_id) + MessageSegment.at(event.user_id) + reply)
    logger.info(
        f"User {event.user_id} 调用poegpt\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"提问: {msg}\n"
        f"回答: {text}"
    )
    access_count(matcher.plugin_name, event)
    access_cd(matcher.plugin_name, event)


@set_reply_mode.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if not await checker_admin(event, bot):
        await matcher.finish("仅管理员可以设置应答模式")
    # 参数解析
    target_id = None
    reply_mode = arg.extract_plain_text().strip()
    if checker_super(event, bot):
        obj = reply_mode.split()
        if len(obj) > 1:
            if obj[0].isdigit():
                target_id = obj[0]
            else:
                await matcher.finish("设定目标必须为群号/QQ号")
            reply_mode = ' '.join(obj[1:])
        elif len(obj) == 1:
            reply_mode = obj[0]

    avail_reply_modes = get_avail_reply_modes()
    if not reply_mode:
        await matcher.finish("设定的应答模式不能为空！\n当前可用的应答模式有" + ','.join(avail_reply_modes.keys()))
    for each_reply_mode in avail_reply_modes.keys():
        if each_reply_mode == reply_mode:
            reply_mode = avail_reply_modes[each_reply_mode]
            break
    else:
        await matcher.finish("设定的应答模式不存在！\n当前可用的应答模式有" + ','.join(avail_reply_modes.keys()))
        return
    session_owner = get_session_owner(event, target_id)
    bing_session_data.set_reply_mode(session_owner, reply_mode)
    logger.info(
        f"User {event.user_id}\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"设置应答模式: {reply_mode}"
    )
    await matcher.finish(f"你设定的应答模式为：{reply_mode}")


@bingchat.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await matcher.finish("你问了什么嘛？", at_sender=True)
    session_owner = get_session_owner(event)
    text = await ask('bing', session_owner, msg)
    if text is None:
        await matcher.finish("消息太快了，请稍后再试！", at_sender=True)
    reply = await handle_msg(text)
    if isinstance(event, PrivateMessageEvent):
        await matcher.send(reply)
    else:
        await matcher.send(MessageSegment.reply(event.message_id) + MessageSegment.at(event.user_id) + reply)
    logger.info(
        f"User {event.user_id} 调用binggpt\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"提问: {msg}\n"
        f"回答: {text}"
    )
    access_count(matcher.plugin_name, event)
    access_cd(matcher.plugin_name, event)


@refresh_chat.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if not await checker_admin(event, bot):
        await matcher.finish("仅管理员可以刷新对话")
    # 参数解析
    target_id = None
    if checker_super(event, bot):
        target_id = arg.extract_plain_text().strip()
    session_owner = get_session_owner(event, target_id)
    gpt_session_data.del_session(session_owner)
    logger.info(
        f"User {event.user_id}\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"刷新gpt对话"
    )
    await matcher.finish(f"刷新会话成功，之前设定的模型与人格仍会在新对话中保留")


@gptchat.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await matcher.finish("你问了什么嘛？", at_sender=True)
    session_owner = get_session_owner(event)
    text = await ask('gpt', session_owner, msg)
    if text is None:
        await matcher.finish("消息太快了，请稍后再试！", at_sender=True)
    reply = await handle_msg(text)
    if isinstance(event, PrivateMessageEvent):
        await matcher.send(reply)
    else:
        await matcher.send(MessageSegment.reply(event.message_id) + MessageSegment.at(event.user_id) + reply)
    logger.info(
        f"User {event.user_id} 调用chatgpt\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"提问: {msg}\n"
        f"回答: {text}"
    )
    access_count(matcher.plugin_name, event)
    access_cd(matcher.plugin_name, event)
