from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot, Message, MessageEvent,
    PrivateMessageEvent, MessageSegment, GroupMessageEvent
)
from nonebot.params import CommandArg, Matcher
from nonebot.permission import SUPERUSER
from services import logger
from .config import config, need_at, matcher_params
from .store import knd_preset, ai_preset, user_session, user_lock, setting
from .utils import Session, get_user_session, handle_msg, checker_super, checker_admin, get_session_owner

__plugin_name__ = "ChatGPT"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    使用OpenAI的ChatGPT进行沟通，因服务器性能有限，仅在特定群开放
    指令：
        chat/Chat/CHAT [文本]                ： 请求ChatGPT的回复
        
        查看对话/会话                     ： 查看已保存的所有会话名称
        重置对话/会话                     ： 重置会话记录，开始新的对话，仅群管可用
        刷新对话/会话                     ： 同上，仅群管可用
        导出对话/会话  [会话名称]           ： 导出当前会话记录，仅群管可用
        导入对话/会话  [会话名称]           ： 导入会话名称对应的会话记录，这会替换当前的会话，仅群管可用
        
        当前人格                         ：查看当前人格设定
        设置人格 [人格]                   ：设置当前人格，仅群管可用，需要具有一定话术水平才能催眠chatgpt
        重置人格                         ：重置人格为默认chatgpt人格，仅群管可用
    注意:
        可用的人格设定默认有 "奏宝"、"ai" 两种，当然ai风格也可以自行设定，[人格]填写自己的催眠话术即可
        使用ChatGPT进行连续会话时，采用的是一个群聊共享相同上下文的形式
        此bot目前调用api接口，使用的是免费额度，额度用完后会再替换成网页版接口
""".strip()
__plugin_superuser_usage__ = """
    指令：
        设置会话模式 [public/全局、group/群聊、user/用户]       :默认为group，会重置所有未保存的会话信息
        图片渲染                                            :默认为开启
        当前模型                                            :默认为gpt-3.5-turbo
        删除对话/会话 [会话名称/会话id]                        : 删除对应会话记录
"""
__plugin_settings__ = {
    "level": 6,
    "cmd": ['ChatGPT', 'chat', 'chatgpt', 'gpt']
}


# 检查项
switch_mode = on_command("设置会话模式", priority=5, block=True, permission=SUPERUSER, **need_at)
switch_img = on_command("图片渲染", priority=5, block=True, permission=SUPERUSER, **need_at)
current_model = on_command("当前模型", priority=5, block=True, permission=SUPERUSER, **need_at)
# 人格
current_preset = on_command("当前人格", aliases={"查看人格"}, priority=5, block=True, **need_at)
reset_preset = on_command("重置人格", aliases={"刷新人格"}, priority=5, block=True, **need_at)
set_preset = on_command("设置人格", aliases={"人格设置"}, priority=5, block=True, **need_at)
# 会话
list_chat = on_command("查看会话", aliases={"查看对话"}, priority=5, block=True, **need_at)
reset_chat = on_command("重置会话", aliases={"重置对话", "刷新对话", "刷新会话"}, priority=5, block=True, **need_at)
load_chat = on_command("导入会话", aliases={"导入对话"}, priority=5, block=True, **need_at)
dump_chat = on_command("导出会话", aliases={"导出对话"}, priority=5, block=True, **need_at)
del_chat = on_command("删除会话", aliases={"删除对话"}, priority=5, block=True, permission=SUPERUSER, **need_at)
# 聊天
gpt3 = on_command(priority=4, block=True, **matcher_params)


@switch_mode.handle()
async def _(matcher: Matcher, event: MessageEvent):
    chat_mode = event.get_plaintext().strip()
    chat_mode = {
        'user': 'user', '用户': 'user',
        'group': 'group', '群聊': 'group',
        'public': 'public', '全局': 'public'
    }.get(chat_mode, '')
    if not chat_mode:
        await matcher.finish('输入的聊天模式不对，只能支持输入用户、群聊、全局!')
    if chat_mode == setting.config['chatmode']:
        await matcher.finish(f'这已经是当前的模式了，无需切换')
    user_session.clear()
    setting.config['chatmode'] = chat_mode
    setting.save()
    await matcher.finish(f'已切换为 {chat_mode} 模式')


@switch_img.handle()
async def _(matcher: Matcher):
    setting.config['send_image'] = not setting.config['send_image']
    setting.save()
    if setting.config['send_image']:
        await matcher.finish('已打开图片渲染')
    else:
        await matcher.finish('已关闭图片渲染')


@current_model.handle()
async def _(matcher: Matcher):
    await matcher.finish(f"当前的模型：{setting.config['model']}")


@current_preset.handle()
async def _(matcher: Matcher, event: MessageEvent):
    session_owner = get_session_owner(event)
    preset = get_user_session(session_owner).preset
    if preset:
        if preset == knd_preset:
            preset = '奏宝'
        elif preset == ai_preset:
            preset = 'ai'
        await matcher.finish(f"当前的人格是：{preset}")
    else:
        await matcher.finish('当前还没有设定的人格哦')


@reset_preset.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if setting.config['chatmode'] == 'public':
        if not checker_super(event, bot):
            await matcher.finish("目前为共享会话模式，仅master可以重置人格")
    elif setting.config['chatmode'] == 'group':
        if not await checker_admin(event, bot):
            await matcher.finish("目前为群聊会话模式，仅管理员可以重置人格")
    obj = ''
    if checker_super(event, bot):
        obj = arg.extract_plain_text().strip()
        if not obj.isdigit():
            obj = ''
    session_owner = get_session_owner(event, obj)
    get_user_session(session_owner).reset_preset()
    if session_owner in setting.preset.keys():
        setting.preset.pop(session_owner)
        setting.save()
    logger.info(f"User {event.user_id} Group {event.group_id if hasattr(event, 'group_id') else '无'} 重置人格")
    await matcher.finish("人格已重置")


@set_preset.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if setting.config['chatmode'] == 'public':
        if not checker_super(event, bot):
            await matcher.finish("目前为共享会话模式，仅master可以设定人格")
    elif setting.config['chatmode'] == 'group':
        if not await checker_admin(event, bot):
            await matcher.finish("目前为群聊会话模式，仅管理员可以设定人格")
    # 参数解析
    target_id = None
    preset = ''
    obj = arg.extract_plain_text().strip().split()
    if setting.config['chatmode'] == 'public' and checker_super(event, bot):
        if len(obj) > 1:
            if obj[0].isdigit():
                target_id = obj[0]
            else:
                await matcher.finish("设定目标必须为群号或QQ号")
            preset = ' '.join(obj[1:])
        elif len(obj) == 1:
            preset = obj[0]
    else:
        preset = ' '.join(obj)
    if not preset:
        await matcher.finish("人格的设定不能为空！")
    session_owner = get_session_owner(event, target_id)
    now_preset = get_user_session(session_owner).set_preset(preset)
    setting.preset[session_owner] = now_preset
    setting.save()
    if now_preset == knd_preset:
        now_preset = '奏宝'
    elif preset == ai_preset:
        now_preset = 'ai'
    logger.info(
        f"User {event.user_id}\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"设置人格: {now_preset}"
    )
    await matcher.finish(f"你设定的新人格为：{now_preset}")


@list_chat.handle()
async def _(event: MessageEvent):
    reply = ''
    cnt = 1
    owner = get_session_owner(event)
    for session in setting.session:
        if session['owner'] == owner:
            reply += f'{cnt}: {session["name"]}'
            cnt += 1
    if not reply:
        await list_chat.finish(f"当前还没有任何保存的会话哦")
    else:
        await list_chat.finish(f"已保存的会话有:\n{reply}")


@reset_chat.handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    if setting.config['chatmode'] == 'public':
        if not checker_super(event, bot):
            await matcher.finish("目前为共享会话模式，仅master可以重置会话")
    elif setting.config['chatmode'] == 'group':
        if not await checker_admin(event, bot):
            await matcher.finish("目前为群聊会话模式，仅管理员可以重置会话")
    obj = ''
    if checker_super(event, bot):
        obj = arg.extract_plain_text().strip()
        if not obj.isdigit():
            obj = ''
    session_owner = get_session_owner(event, obj)
    get_user_session(session_owner).reset()
    logger.info(f"User {event.user_id} Group {event.group_id if hasattr(event, 'group_id') else '无'} 重置会话")
    await matcher.finish("会话已重置")


@load_chat.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    session_owner = get_session_owner(event)
    session_name = arg.extract_plain_text().strip()
    if not session_name:
        await matcher.finish('你没有带上要导入的会话名字嘛')
    reply = get_user_session(session_owner).load_user_session(session_name, session_owner)
    if not reply:
        reply = '未找到此会话，可以发送"查看对话"获取当前已导出的对话'
    setting.preset[session_owner] = user_session[session_owner].preset
    setting.save()
    logger.info(f"User {event.user_id} Group {event.group_id if hasattr(event, 'group_id') else '无'} 导入对话 {session_name}")
    if isinstance(event, GroupMessageEvent):
        await matcher.finish(MessageSegment.reply(event.message_id) + reply)
    else:
        await matcher.finish(reply)


@dump_chat.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    session_owner = get_session_owner(event)
    session_name = arg.extract_plain_text().strip()
    if not session_name:
        await matcher.finish('你没有带上要导出的会话名字嘛')
    if session_name.isdigit():
        await matcher.finish('会话名字不能是纯数字！')
    for session in setting.session:
        if session['name'] == session_name and session['owner'] == session_owner:
            await matcher.finish("此会话名称已被使用，请使用别的名称")
            return
    logger.info(f"User {event.user_id} Group {event.group_id if hasattr(event, 'group_id') else '无'} 导出对话 {session_name}")
    if isinstance(event, GroupMessageEvent):
        await matcher.finish(
            MessageSegment.reply(event.message_id) + get_user_session(session_owner).dump_user_session(session_name, session_owner)
        )
    else:
        await matcher.finish(get_user_session(session_owner).dump_user_session(session_name, session_owner))


@del_chat.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await matcher.finish('你没有带上要删除的会话名字/id嘛')
    if msg.isdigit():
        _index = int(msg) - 1
        if 0 <= _index <= len(setting.session) - 1:
            session_name = setting.session[_index]['name']
            setting.session.pop(_index)
            setting.save()
            await matcher.send(f"成功删除会话 {session_name}")
        else:
            await matcher.finish('输入的会话id有误！')
            return
    else:
        for session in setting.session:
            if session['name'] == msg:
                session_name = msg
                setting.session.remove(session)
                setting.save()
                await matcher.send(f"成功删除会话 {msg}")
                break
        else:
            await matcher.finish(f"输入的会话名称有误！")
            return
    logger.info(f"User {event.user_id} Group {event.group_id if hasattr(event, 'group_id') else '无'} 删除对话 {session_name}")


@gpt3.handle()
async def _(matcher: Matcher, event: MessageEvent, bot:Bot, arg: Message = CommandArg()):
    session_owner = get_session_owner(event)
    msg = arg.extract_plain_text().strip()
    if not msg:
        await matcher.finish("你问了什么嘛？", at_sender=True)
        return
    if session_owner in user_lock and user_lock[session_owner]:
        await matcher.finish("消息太快啦～请稍后", at_sender=True)
        return
    user_lock[session_owner] = True
    resp = await get_user_session(session_owner).get_chat_response(msg, checker_super(event, bot))
    resp = await handle_msg(resp)
    if isinstance(event, PrivateMessageEvent):
        await matcher.send(resp)
    else:
        await matcher.send(MessageSegment.reply(event.message_id) + resp, at_sender=True)
    user_lock[session_owner] = False
    logger.info(
        f"User {event.user_id} 调用chatgpt\n"
        f"Group {event.group_id if hasattr(event, 'group_id') else '无'}\n"
        f"提问: {msg}\n"
        f"回答: {resp}"
    )
