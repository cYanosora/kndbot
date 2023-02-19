import asyncio
import random
import re
from typing import Union
from nonebot import on_regex
from nonebot.log import logger
from nonebot import on_notice, on_command, on_message
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, MessageSegment, Message
from nonebot.matcher import Matcher
from nonebot.typing import T_Handler, T_State
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters import Bot

from configs.config import NICKNAME
from utils.limit_utils import ignore_mute
from .data_source import commands
from .rule import retry_rule, check_rule, poke_rule, normal_rule
from .models import Command, retry_manager, UserInfo
from .utils import ReplyBank, get_user_info

__plugin_name__ = "互动"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    {NICKNAME}可以对一些关键词做出各种反应，而且说不定有时还会索求你作出一些特定回复的样子噢？
    这里列出一些常见的关键词(需要艾特)：
    戳一戳、夸可爱、叫laopo、嗦面、奏门、骂人、今日运势(幸运曲)、一些和奏有关系的sekai角色的名字
    除此之外，还有一些整活向关键词等等就需要你日常使用时慢慢发掘啦，虽然很少也很难被触发(ˉ▽ˉ；)...
    
    注意：
        * 部分回复的文案内容与好感度相关, 详见签到功能 *
        * 文案语料库在以极其缓慢的速度更新中 *
        
        * 功能存在的时间已久，部分旧文案可能已经ooc (ﾉω･､)*
        * 但语料库本身十！分！缺！文！案！而且维护语料库比较麻烦，姑且不修改or删除(*￣3￣) *
        
        * 有好玩的需要特定回复的词条可以联系管理添加，哦内该 ヾ(_ _。） *
        * master属性all奏all杂食，无需担心会被文案雷到(但会被ooc的文案创到)*

        * 文案内容偏向于还原可爱(目前是占压倒性的主要成分)、亚萨西、怕生、呆萌、容易害羞（下接） *
        * 体力差、自我谴责、阴郁、作曲脑、音乐宅、完全夜行性、偶尔又会突然很帅气高冷等等等的奏。*
        * 没错，定了个基本完全还原奏的目标，但对于master的水平而言感觉是在挑战不可能 *
        * 所以还请不要太期待master一个人的力量能把奏宝从游戏里带出来(画大饼ing *
""".strip()
__plugin_settings__ = {
    "cmd": ["互动", "随机消息回复", "随机消息", "随机回复", "娱乐功能"],
}
__plugin_block_limit__ = {}


retry = on_message(priority=3, rule=retry_rule(), block=True)


async def send_msg(matcher: Matcher, res: Union[Message, MessageSegment, str]):
    if isinstance(res, str):
        fin_msg = await ReplyBank.get_final_reply_list(res)
    else:
        fin_msg = [res]
    for index, per in enumerate(fin_msg, 1):
        if per:
            await matcher.send(per)
            if index != len(fin_msg):
                await asyncio.sleep(random.randint(1, 3))


@retry.handle()
async def _(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
    # 开始这轮对话
    retry_info = retry_manager.get(event.user_id, event.group_id)
    args = retry_info['args']
    kwargs = retry_info['kwargs']
    user = UserInfo(
        qq=event.user_id,
        group=event.group_id,
        text=event.get_plaintext().strip(),
        state=retry_info['state'],
        cid=retry_info['cid']
    )
    await get_user_info(bot, user)
    # 找到用户所处对话的函数cid
    for each in commands:
        if each.id == user.cid:
            cmd: Command = each
            break
    else:
        return
    # 收到无文本消息，自动拒绝
    if not user.text:
        ignore_mute(f"{user.group}_{user.qq}")
        if retry_info['cnt'] >= 3:
            retry_manager.remove(user.qq, user.group)
            return
        else:
            retry_manager.add(user.qq, user.group, cmd.id, user.state)
    raw_st = user.state
    # 触发对话处理函数，获取 回复内容、新状态
    res, user.state = await cmd.func(user, *args, **kwargs)
    # 新状态值为-1，视为触发其他命令，若此状态触发3次基本说明用户不想在继续对话的retry，则删除retry信息
    if user.state == -1:
        ignore_mute(f"{user.group}_{user.qq}")
        matcher.open_propagation()
        # 将未成功触发对话的用户加入retry名单(不重复添加, 若存在则cnt+1)
        retry_manager.add(user.qq, user.group, cmd.id, raw_st)
        # 若此用户retry次数超标，删除此信息
        if retry_info['cnt'] >= 3:
            retry_manager.remove(user.qq, user.group)
        await retry.finish()
    # 若有回复
    if res:
        # 删除retry信息
        retry_manager.remove(user.qq, user.group)
        # 新状态值为0，视为对话结束，retry信息彻底消失
        if user.state == 0:
            await send_msg(matcher, res)
            await retry.finish()
        # 新状态值非0，视为继续对话，重新添加retry信息
        else:
            # 下一个状态
            retry_manager.add(user.qq, user.group, cmd.id, user.state)
            await send_msg(matcher, res)
    # 若明明该有回复却无回复(出bug了)
    else:
        ignore_mute(f"{user.group}_{user.qq}")
        logger.warning(f"随机消息模块多轮对话无消息内容!\n用户消息：{user.text}")


def create_matchers():
    def execute_handler(cmd: Command) -> [T_Handler]:
        @test.handle()
        async def _(matcher:Matcher, bot: Bot, state: T_State):
            # 补全用户信息
            user: UserInfo = state["users"]
            await get_user_info(bot, user)
            # 对话有多轮
            if cmd.next:
                res, user.state = await cmd.func(user)
            else:
                res = await cmd.func(user)
            if res:
                # 状态值为0，对话结束
                if user.state == 0:
                    await send_msg(matcher, res)
                    await test.finish()
                # 状态值非0，对话继续，将用户添加进retry名单
                else:
                    retry_manager.add(user.qq, user.group, cmd.id, user.state)
                    await send_msg(matcher, res)
            else:
                ignore_mute(f"{user.group}_{user.qq}")
                logger.warning(f"随机消息模块单轮对话无消息内容!\n用户消息：{user.text}")
            return

    for command in commands:
        if command.mode == "reg":
            test = on_regex(
                pattern=command.reg,
                flags=re.I,
                rule=check_rule(command),
                permission=GROUP,
                priority=command.priority,
                block=True,
            )
            execute_handler(command)
        elif command.mode == "ntc":
            test = on_notice(
                rule=poke_rule(command),
                priority=command.priority,
                block=False
            )
            execute_handler(command)
        elif command.mode == "cmd":
            test = on_command(
                cmd=command.reg,
                rule=normal_rule(command),
                aliases=command.alias,
                permission=GROUP,
                priority=command.priority,
                block=True
            )
            execute_handler(command)
        else:
            continue


create_matchers()
