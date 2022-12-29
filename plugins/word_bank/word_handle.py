import re
from typing import Tuple, Any
from utils.utils import is_number
from nonebot.params import CommandArg, RegexGroup, Command
from nonebot.exception import FinishedException
from services.log import logger
from configs.path_config import DATA_PATH
from utils.message_builder import custom_forward_msg
from ._model import WordBank
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, PrivateMessageEvent
from nonebot import on_command, on_regex
from manager import Config
from ._data_source import delete_word, show_word
from ._config import scope2int, type2int

__plugin_name__ = "词库问答 [Admin]"
__plugin_type__ = "词条管理"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    对指定问题的随机回答，对相同问题可以设置多个不同回答
    自定义词条优先级低于随机消息回复功能，这可能会导致有些词条无响应
    自定义词条如果非必要请尽量不要含图片，容易被风控，尤其动图
    自定义词条含有图片、艾特、qq黄豆表情时，查看、删除词条的指令只能使用下标方式代替问句！
    删除词条后每个词条的id可能会变化，请查看后再删除
    指令：
        添加词条 ?[模糊/正则]问...答...            :添加问答词条，可重复添加相同问题的不同回答
        删除词条 [问题/下标] ?[下标]               :删除指定问句的指定下标回答或全部回答
        查看词条 ?[问题/下标]                     :查看全部词条或对应词条的答句 
    示例：
        添加词条问谁是奏宝答是我                  :向"谁是奏宝"此问句添加新的答句"是我"
        添加词条模糊问谁是奏宝答是我               :同上，但匹配模式为消息中一旦含有此问句都会触发
        添加词条正则问谁是奏宝答是我               :同上，但匹配模式为满足正则条件则触发，不懂什么是正则不要去用
        删除词条 谁是奏宝                       :删除"谁是奏宝"问句的所有答句
        删除词条 谁是奏宝 0                     :删除"谁是奏宝"问句中下标为0的答句
        删除词条 id:0                         :删除下标为0的问句的所有答句
        查看词条                              :查看此群所有的问句以及由bot主设置的全局问句
        查看词条 谁是奏宝                       :查看问句"谁是奏宝"的所有答句
        查看词条 id:0                         :查看下标为0的问句的所有答句
""".strip()
__plugin_superuser_usage__ = """
superuser_usage:
    在私聊中超级用户额外设置
    指令：
        添加全局词条 ?(模糊|正则)?问\s*?(\S*\s?\S*)\s*?答\s?(\S*)
        删除全局词条
"""
__plugin_settings__ = {
    "admin_level": Config.get_config("word_bank", "WORD_BANK_LEVEL [LEVEL]"),
    "cmd": ["词库问答", "添加词条", "删除词条", "查看词条"],
}

data_dir = DATA_PATH / "word_bank"
data_dir.mkdir(parents=True, exist_ok=True)

add_word = on_regex(
    r"^添加(全局|私聊)?词条\s*?(模糊|正则)?问\s*?(\S*\s?\S*)\s*?答\s?(\S*)", priority=5, block=True
)

delete_word_matcher = on_command("删除词条", aliases={'删除全局词条'}, priority=5, block=True)

show_word_matcher = on_command("显示词条", aliases={"查看词条"}, priority=5, block=True)


@add_word.handle()
async def _(
    bot: Bot,
    event: MessageEvent,
    reg_group: Tuple[Any, ...] = RegexGroup(),
):
    # 私聊、全局只允许超管使用
    word_scope, word_type, problem, answer = reg_group
    if (
        (isinstance(event, PrivateMessageEvent) or word_scope)
        and str(event.user_id) not in bot.config.superusers
    ):
        return
    word_type = type2int.get(word_type, 0)
    if isinstance(event, PrivateMessageEvent):
        word_scope = scope2int.get(word_scope, 2)
    else:
        word_scope = scope2int.get(word_scope, 1)
    # print('词条参数：', word_scope,word_type,problem,answer)
    # 检测词条完整性
    if not problem.strip():
        await add_word.finish("词条问题不能为空！")
    if not answer.strip():
        await add_word.finish("词条回答不能为空！")
    try:
        # 对正则问题额外配置
        if word_type == 2:
            try:
                re.compile(problem)
            except re.error:
                await add_word.finish(f"添加词条失败，正则表达式 {problem} 非法！")
        await WordBank.add_problem_answer(
            event.user_id,
            event.group_id if isinstance(event, GroupMessageEvent) and word_scope == 1 else 0,
            word_scope,
            word_type,
            problem,
            answer,
        )
    except Exception as e:
        if isinstance(e, FinishedException):
            await add_word.finish()
        raise e
        # logger.error(
        #     f"(USER {event.user_id}, GROUP "
        #     f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
        #     f" 添加词条 {problem} 发生错误 {type(e)}: {e} "
        # )
        # await add_word.finish(f"添加词条 {problem} 发生错误！")
    await add_word.send("添加词条 " + Message(problem) + " 成功！")
    logger.info(
        f"(USER {event.user_id}, GROUP "
        f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
        f" 添加词条 {problem} 成功！"
    )


@delete_word_matcher.handle()
async def _(
        bot: Bot,
        event: MessageEvent,
        cmd: Tuple[str, ...] = Command(),
        arg: Message = CommandArg()
):
    if (
        (isinstance(event, PrivateMessageEvent) or "全局" in cmd[0])
        and str(event.user_id) not in bot.config.superusers
    ):
        return
    if not (msg := arg.extract_plain_text().strip()):
        await delete_word_matcher.finish(
            "此命令之后需要跟随指定词条，通过“显示词条“查看\n"
            "注：设置的问题中含有图片、艾特、qq黄豆表情时只能使用问题的下标删除"
        )
    if isinstance(event, GroupMessageEvent):
        result = await delete_word(msg, event.group_id)
    else:
        result = await delete_word(msg, word_scope=2 if cmd[0] == '删除词条' else 0)
    await delete_word_matcher.send(result)
    logger.info(
        f"(USER {event.user_id}," +
        (f" GROUP {event.group_id})" if isinstance(event, GroupMessageEvent) else "PRIVATE") +
        f" 删除词条:" + msg
    )


@show_word_matcher.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    id_ = gid = None
    # 显示指定问题的回答 or 显示群聊全部问题的回答
    if problem := arg.extract_plain_text().strip():
        # 查看方式为问题下标
        if problem.startswith("id:"):
            id_ = problem.split(":")[-1]
            if (
                not is_number(id_)
                or int(id_) < 0
                or int(id_)
                >= len(await WordBank.get_group_all_problem(event.group_id))
            ):
                await show_word_matcher.finish("id必须为数字且在范围内")
            id_ = int(id_)
        # 查看方式为指定群号
        elif problem.startswith("gid:"):
            gid = problem.split(":")[-1]
            if (
                not is_number(gid)
                or int(gid) < 0
                or int(gid)
                >= len(await WordBank.get_problem_by_scope(0))
            ):
                await show_word_matcher.finish("gid必须为数字且在范围内")
            gid = int(gid)
    msg_list = await show_word(problem, id_, gid, None if gid else event.group_id)
    # 处理无词条的一些情况
    if isinstance(msg_list, str):
        await show_word_matcher.finish(msg_list)
    # 使用合并转发返回词条结果
    else:
        await bot.send_group_forward_msg(
            group_id=event.group_id, messages=custom_forward_msg(msg_list, bot.self_id)
        )
        logger.info(
            f"(USER {event.user_id}, GROUP "
            f"{event.group_id if isinstance(event, GroupMessageEvent) else 'private'})"
            f" 发送查看词条回答:" + problem
        )


@show_word_matcher.handle()
async def _(event: PrivateMessageEvent, arg: Message = CommandArg()):
    id_ = gid = None
    # 显示指定问题的回答，或指定群聊的所有问题
    if problem := arg.extract_plain_text().strip():
        if problem.startswith("id:"):
            id_ = problem.split(":")[-1]
            if (
                not is_number(id_)
                or int(id_) < 0
                or int(id_)
                > len(await WordBank.get_problem_by_scope(2))
            ):
                await show_word_matcher.finish("id必须为数字且在范围内")
            id_ = int(id_)
        elif problem.startswith("gid:"):
            gid = problem.split(":")[-1]
            if (
                not is_number(gid)
                or int(gid) < 0
                or int(gid)
                > len(await WordBank.get_problem_by_scope(0))
            ):
                await show_word_matcher.finish("gid必须为数字且在范围内")
            gid = int(gid)
        msg_list = await show_word(problem, id_, gid, word_scope=2 if id_ is not None else None)
    # 显示所有私聊问题的回答
    else:
        msg_list = await show_word(problem, None, None, word_scope=2)
    if isinstance(msg_list, str):
        await show_word_matcher.send(msg_list)
    else:
        t = ""
        for msg in msg_list:
            t += msg + '\n'
        await show_word_matcher.send(t[:-1])
    logger.info(
        f"(USER {event.user_id}, GROUP "
        f"private)"
        f" 发送查看词条回答:" + problem
    )
