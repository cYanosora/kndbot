from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.rule import to_me
from playwright._impl._api_types import Error as PlaywrightAPIError
from models.level_user import LevelUser
from utils.limit_utils import access_cd
from utils.message_builder import reply
from .chatgpt import Chatbot
from .config import config
from .data import setting
from .utils import Session, create_matcher
from utils.utils import htmlrender, scheduler
md_to_pic = htmlrender.md_to_pic

__plugin_name__ = "ChatGPT"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    使用OpenAI的ChatGPT进行沟通，因服务器性能有限，仅在特定群开放
    此bot使用的是免费版，所以回复需要耐心等待(约20字/s)，慢的要死，Plus版快2倍以上且稳定，但20$/mo
    受网络环境和chatGPT负载影响，请求可能会经常失败，并且有时回复只有一半而没有下文了，不要期待这个功能的可用性
    指令：
        chat/Chat/CHAT [文本]                 ： 请求ChatGPT的回复
        @bot 刷新对话/会话                     ： 重置会话记录，开始新的对话
        @bot 导出对话/会话                     ： 导出当前会话记录
        @bot 导入对话/会话  [会话ID] *[父消息ID] ： 将会话记录导入，这会替换当前的会话，父消息ID可以不用携带
        @bot 加载对话/会话  [会话ID] *[父消息ID] ： 同上，将会话记录导入，这会替换当前的会话，父消息ID可以不用携带
        @bot 保存对话/会话  [会话名称]           ： 将当前会话保存
        @bot 查看对话/会话                     ： 查看已保存的所有会话
        @bot 切换对话/会话  [会话名称]           ： 切换到指定的会话
        @bot 回滚对话/会话  *[数字]             ： 返回到之前的会话，输入数字可以返回多个会话，但不可以超过最大支持数量
    注意:
        使用ChatGPT进行连续会话时，采用的是一个群聊共享相同上下文的形式(因为openai对使用独立上下文有数量限制)
        刷新、导入、切换、回滚对话的指令只有管理员可以使用
        限制每个群一分钟内只能请求两次ChatGPT，但实际能成功一次就不错了()
        ================================================================
        功能来自https://github.com/A-kirami/nonebot-plugin-chatgpt
        master只是做了一些微小改动而已，此功能可能会因为openai网页结构变更导致失效，若无法正常使用可以告诉master
        ChatGPT现在被削了很多，不要期待能养出奏宝的人格，嗯，至少我不能。
""".strip()
__plugin_settings__ = {
    "level": 6,
    "cmd": ['ChatGPT', 'chat', 'chatgpt', 'gpt']
}
__plugin_cd_limit__ = {"cd": 60, "limit_type": "group", "count_limit": 2, "rst": "别急，[cd]s后再用！"}
__plugin_block_limit__ = {"rst": "别急，正在等待ChatGPT回复！", "limit_type": "group"}


matcher = create_matcher(
    config.chatgpt_command,   # chat,Chat,CHAT
    config.chatgpt_to_me,     # false
    config.chatgpt_private,   # true
    config.chatgpt_priority,  # 5
    config.chatgpt_block,     # true
)
refresh = on_command("刷新对话", aliases={"刷新会话"}, block=True, rule=to_me(), priority=5)
save = on_command("保存对话", aliases={"保存会话"}, block=True, rule=to_me(), priority=5)
export = on_command("导出对话", aliases={"导出会话"}, block=True, rule=to_me(), priority=5)
import_ = on_command("导入对话", aliases={"导入会话", "加载对话", "加载会话"}, block=True, rule=to_me(), priority=5)
check = on_command("查看对话", aliases={"查看会话"}, block=True, rule=to_me(), priority=5)
switch = on_command("切换对话", aliases={"切换会话"}, block=True, rule=to_me(), priority=5)
rollback = on_command("回滚对话", aliases={"回滚会话"}, block=True, rule=to_me(), priority=5)
chat_bot = Chatbot(
    token=setting.token or config.chatgpt_session_token,  # 优先使用setting保存的实时token
    account=config.chatgpt_account,
    password=config.chatgpt_password,
    api=config.chatgpt_api,             # https://chat.openai.com/
    proxies=config.chatgpt_proxies,     # None
    timeout=config.chatgpt_timeout,     # 60s
)

session = Session(config.chatgpt_scope)


async def check_purview(event: MessageEvent) -> bool:
    """检查是否为群聊群管or5级bot管理员"""
    group_id = event.group_id if hasattr(event, 'group_id') else 0
    flag = await LevelUser.check_level(event.user_id, group_id, 5)
    return flag or not (
        isinstance(event, GroupMessageEvent)
        and config.chatgpt_scope == "public"
        and event.sender.role == "member"
    )


@matcher.handle()
async def ai_chat(event: MessageEvent, arg: Message = CommandArg()) -> None:
    # 若上下文关联器从没有开启过，先开一下
    if not chat_bot.content:
        await chat_bot.playwright_start()
    # 获取用户输入
    text = arg.extract_plain_text().strip()
    if not text:
        await matcher.finish("什么也没有发嘛，你是在等ChatGPT主动找你聊天吗？Σ(っ °Д °;)っ", at_sender=True)
    else:
        await matcher.send("收到，正在请求ChatGPT，请耐心等待", at_sender=True)
    msgid = event.message_id
    try:
        msg = await chat_bot(**session[event]).get_chat_response(text)
        # 旧token失效，使用config新设置的token
        if (msg == "token失效，请重新设置token") and (
            chat_bot.session_token != config.chatgpt_session_token
        ):
            logger.warning('token失效，正在尝试重新获取token...')
            await chat_bot.set_cookie(config.chatgpt_session_token)
            msg = await chat_bot(**session[event]).get_chat_response(text)
    # 没能正常获取到回复
    except PlaywrightAPIError as e:
        error = f"{type(e).__name__}: {e}"
        logger.opt(exception=e).error(f"ChatGPT request failed: {error}")
        if type(e).__name__ == "TimeoutError":
            await matcher.finish("ChatGPT回复已超时。", at_sender=True)
        elif type(e).__name__ == "Error":
            msg = "ChatGPT 目前无法回复您的问题。"
            if config.chatgpt_detailed_error:
                msg += f"\n{error}"
            else:
                msg += "\n可能的原因是同时提问过多，问题过于复杂等。"
            await matcher.finish(msg, at_sender=True)
        return
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        logger.opt(exception=e).error(f"ChatGPT request failed: {error}")
        msg = "ChatGPT 目前无法回复您的问题。"
        if config.chatgpt_detailed_error:
            msg += f"\n{error}"
        else:
            msg += "\n可能的原因是请求时遇到了无法通过的验证码校验等。"
        await matcher.finish(msg)
        return
    logger.info(
        f'User{event.user_id} Group {event.group_id if hasattr(event, "group_id") else 0}\n'
        f'问题：{text}\n'
        f'回复：{msg}'
    )
    # 若设置使用图片回复or文字超过回复上限自动使用图片发送
    if config.chatgpt_image or len(msg) > config.chatgpt_max_textlength:
        if msg.count("```") % 2 != 0:
            msg += "\n```"
        img = await md_to_pic(msg, width=config.chatgpt_image_width)
        msg = MessageSegment.image(img)
    await matcher.send(reply(msgid) + msg, at_sender=True)
    # 记录cd、会话状态
    access_cd(matcher.plugin_name, event)
    session[event] = chat_bot.conversation_id, chat_bot.parent_id


@refresh.handle()
async def refresh_conversation(event: MessageEvent) -> None:
    if not await check_purview(event):
        await import_.finish("你不是管理员，没有权限进行此操作。", at_sender=True)
    del session[event]
    await refresh.finish("当前会话已刷新", at_sender=True)


@export.handle()
async def export_conversation(event: MessageEvent) -> None:
    if cvst := session[event]:
        await export.send(
            f"已成功导出会话:\n"
            f"会话ID: {cvst['conversation_id'][-1]}\n"
            f"父消息ID: {cvst['parent_id'][-1]}\n"
            f"请自己保存好以便之后导入对话哦！",
            at_sender=True
        )
    else:
        await export.finish("你还没有任何会话记录", at_sender=True)


@import_.handle()
async def import_conversation(event: MessageEvent, arg: Message = CommandArg()) -> None:
    if not await check_purview(event):
        await import_.finish("你不是管理员，没有权限进行此操作。", at_sender=True)
    args = arg.extract_plain_text().strip().split()
    if not args:
        await import_.finish("至少需要提供会话ID", at_sender=True)
    if len(args) > 2:
        await import_.finish("提供的参数格式不正确", at_sender=True)
    session[event] = args.pop(0), args[0] if args else None
    await import_.send("已成功导入会话", at_sender=True)


@save.handle()
async def save_conversation(event: MessageEvent, arg: Message = CommandArg()) -> None:
    if not await check_purview(event):
        await save.finish("你不是管理员，没有权限进行此操作。", at_sender=True)
    if session[event]:
        name = arg.extract_plain_text().strip()
        session.save(name, event)
        await save.send(f"已将当前会话保存为: {name}", at_sender=True)
    else:
        await save.finish("你还没有任何会话记录", at_sender=True)


@check.handle()
async def check_conversation(event: MessageEvent) -> None:
    try:
        name_list = "\n".join(list(session.find(event).keys()))
        await check.send(f"已保存的会话有:\n{name_list}", at_sender=True)
    except KeyError:
        await check.send(f"当前并没有任何保存的会话", at_sender=True)


@switch.handle()
async def switch_conversation(event: MessageEvent, arg: Message = CommandArg()) -> None:
    if not await check_purview(event):
        await switch.finish("你不是管理员，没有权限进行此操作。", at_sender=True)
    name = arg.extract_plain_text().strip()
    try:
        session[event] = session.find(event)[name]
        await switch.send(f"已切换到会话: {name}", at_sender=True)
    except KeyError:
        await switch.send(f"找不到会话: {name}", at_sender=True)


@rollback.handle()
async def rollback_conversation(event: MessageEvent, arg: Message = CommandArg()):
    if not await check_purview(event):
        await switch.finish("你不是管理员，没有权限进行此操作。", at_sender=True)
    num = arg.extract_plain_text().strip()
    if num.isdigit():
        num = int(num)
        if session[event]:
            count = session.count(event)
            if num > count:
                await rollback.finish(f"历史会话数不足，当前历史会话数为{count}", at_sender=True)
            else:
                for _ in range(num):
                    session.pop(event)
                await rollback.send(f"已成功回滚{num}条会话", at_sender=True)
        else:
            await save.finish("你还没有任何会话记录", at_sender=True)
    else:
        await rollback.finish(
            f"请输入有效的数字，最大回滚数为{config.chatgpt_max_rollback}", at_sender=True
        )


# 自动刷新token并保存
@scheduler.scheduled_job(
    "interval",
    minutes=config.chatgpt_refresh_interval
)
async def refresh_session() -> None:
    await chat_bot.refresh_session()
    setting.token = chat_bot.session_token
    setting.save()


