import asyncio
# import datetime
import math
import random
import re
from typing import Any, Tuple, Optional
# from apscheduler.triggers.date import DateTrigger
from nonebot import on_regex, on_command, on_message, get_bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, Bot, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.typing import T_State
from models.bag_user import BagUser
from services import logger
from utils.data_utils import init_rank
from utils.imageutils import text2image, pic2b64
# from utils.utils import scheduler
from utils.message_builder import at, image
from ._config import pjskguess, GUESS_MUSIC, GUESS_CARD, PJSK_GUESS, max_tips_count, guess_time, PJSK_ANSWER
from ._data_source import (
    getRandomChart, getRandomJacket, getRandomMusic, getRandomSE,
    cutJacket, cutMusic, cutSE, cutCard, getRandomCard, cutChart
)
from utils.limit_utils import access_count, access_cd
from ._rule import check_rule, check_reply
from ._utils import pre_check, aliasToMusicId, aliasToCharaId
from .._config import BUG_ERROR
from .._models import PjskGuessRank
try:
    import ujson as json
except:
    import json

__plugin_name__ = "pjsk猜卡面/猜曲/猜谱面"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    pjsk猜曲、猜卡面、猜谱面，移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    由于功能容易刷屏，仅在特定群开放
    限制每个群2分钟最多猜1次，每人一天只能猜10次
    指令：
        pjsk猜卡面
        pjsk猜谱面                  ：效果与pjsk谱面猜曲相同
        pjsk [类型] 猜曲            ：[类型]有普通、阴间、非人类、听歌、倒放、谱面几种类型，默认为普通   
""".strip()
__plugin_settings__ = {
    "level": 6,
    "default_status": False,
    "cmd": ["pjsk猜曲", "pjsk猜卡面", "pjsk猜谱面", "烧烤相关", "uni移植"],
}
__plugin_cd_limit__ = {"cd": 1800, "count_limit": 10, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "当前有正在进行的猜卡面/曲目/谱面，请等待结束后再开始", "limit_type": "group"}
__plugin_count_limit__ = {
    "max_count": 10,
    "limit_type": "user",
    "rst": "今天已经猜了[count]次了，还请明天再继续呢[at]",
}

# pjsk猜卡面
pjsk_guesscard = on_regex(
    r'^(?:pjsk|sekai) *(正常|阴间|非人类)? *猜卡面 *(\d*)$',
    flags=re.I, permission=GROUP, priority=5, block=True
)

# pjsk猜曲目
pjsk_guessmusic = on_regex(
    r'^(?:pjsk|sekai) *(正常|阴间|非人类|听歌|倒放|音效|谱面)? *猜曲 *(\d*)$',
    flags=re.I, permission=GROUP, priority=5, block=True
)

# pjsk猜谱面
pjsk_guessmap = on_regex(
    r'^(?:pjsk|sekai) *猜谱面 *$',
    flags=re.I, permission=GROUP, priority=5, block=True
)

pjsk_guessreply = on_message(rule=check_reply(), permission=GROUP, priority=4, block=True)

pjsk_guessrank = on_regex(
    r'^(?:pjsk|sekai) *(?:(正常|阴间|非人类|听歌|倒放|音效|谱面)?(猜曲|猜卡面|猜谱面)) *排[行名]榜? *(\d*)',
    flags=re.I, permission=GROUP, priority=4, block=True
)

pjsk_guesstip = on_command('来点提示', aliases={"来丶提示"}, rule=check_rule(), permission=GROUP, priority=3, block=True)

pjsk_gameover = on_command('结束猜曲', aliases={"结束猜谱面", "结束猜卡面"}, rule=check_rule(), permission=GROUP, priority=3, block=True)


@pjsk_guessreply.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, state: T_State):
    global pjskguess
    answer = state[PJSK_ANSWER]
    if not answer:
        matcher.open_propagation()
    game_type = state[PJSK_GUESS]
    if game_type == GUESS_CARD:
        charaid, name = await aliasToCharaId(answer, event.group_id)
        if charaid == 0:
            await pjsk_guessreply.finish('没有找到你说的角色哦', at_sender=True)
        elif charaid == pjskguess[game_type][event.group_id]['charaid']:
            await endgame(
                event.group_id, event.self_id, GUESS_CARD, event.user_id, True,
                plugin_name=matcher.plugin_name, event=event
            )
        else:
            await pjsk_guessreply.finish(f'您猜错了，答案不是{name}哦', at_sender=True)
    else:
        musicid, name = await aliasToMusicId(answer)
        if musicid == 0:
            await pjsk_guessreply.finish('没有找到你说的歌曲哦', at_sender=True)
        elif musicid == pjskguess[game_type][event.group_id]['musicid']:
            await endgame(
                event.group_id, event.self_id, GUESS_MUSIC, event.user_id, True,
                plugin_name=matcher.plugin_name, event=event
            )
        else:
            await pjsk_guessreply.finish(f'您猜错了，答案不是{name}哦', at_sender=True)


@pjsk_guesscard.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    global pjskguess
    if reply := pre_check(event.group_id):
        await pjsk_guesscard.finish(reply)
    msgs = []
    cardid, charaid, asset, cardname, charaname, rarity = await getRandomCard()
    if not reg_group[0] and not reg_group[1] or reg_group[0] == '正常' or reg_group[1] == '1':
        size, isbw, guessDiff = 250, False, 1
        text = ''
    elif reg_group[0] == '阴间' or reg_group[1] == '2':
        size, isbw, guessDiff = 250, True, 2
        text = '阴间'
    elif reg_group[0] == '非人类' or reg_group[1] == '3':
        size, isbw, guessDiff = 90, False, 3
        text = '非人类'
    else:
        await pjsk_guesscard.finish(BUG_ERROR)
        return
    file, endfile = cutCard(asset, rarity, event.group_id, size, isbw)
    msgs.append(image(b64=pic2b64(text2image(
        f'PJSK{text}卡面竞猜 （随机裁切）\n艾特我+你的答案以参加猜曲（不要使用回复）\n'
        f'\n你有{guess_time}秒的时间回答\n可手动发送“结束猜卡面”来结束猜曲'
    ))))
    msgs.append(MessageSegment.image(f"file:///{file.absolute()}"))
    for msg in msgs:
        await pjsk_guessmusic.send(msg)
    pjskguess[GUESS_CARD][event.group_id] = {
        'isgoing': True, 'diff': guessDiff, 'tips': None,
        'charaid': charaid, 'cardname': cardname, 'cardid': cardid, 'charaname': charaname,
        'userid': event.user_id, 'file': file, 'endfile': endfile
    }
    await asyncio.sleep(guess_time)
    await endgame(event.group_id, event.self_id, GUESS_CARD)
    # 采用scheduler有时会有严重的时间误差
    # delta = datetime.timedelta(seconds=guess_time)
    # trigger = DateTrigger(run_date=datetime.datetime.now() + delta)
    # scheduler.add_job(
    #     func=endgame,
    #     trigger=trigger,
    #     kwargs={'group_id':event.group_id, 'game_type': GUESS_CARD, 'self_id': event.self_id},
    #     # misfire_grace_time=5,
    # )


@pjsk_guessmusic.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    global pjskguess
    if reply := pre_check(event.group_id):
        await pjsk_guesscard.finish(reply)
    msgs = []
    if not reg_group[0] and not reg_group[1] or reg_group[0] == '正常' or reg_group[1] == '1':
        musicid, musicname, asset = await getRandomJacket()
        file, endfile = cutJacket(asset, event.group_id, size=140, isbw=False)
        guessDiff = 1
        text = '曲绘'
        msgs.append(MessageSegment.image(f"file:///{file.absolute()}"))
    elif reg_group[0] == '阴间' or reg_group[1] == '2':
        musicid, musicname, asset = await getRandomJacket()
        file, endfile = cutJacket(asset, event.group_id, size=140, isbw=True)
        guessDiff = 2
        text = '阴间曲绘'
        msgs.append(MessageSegment.image(f"file:///{file.absolute()}"))
    elif reg_group[0] == '非人类' or reg_group[1] == '3':
        musicid, musicname, asset = await getRandomJacket()
        file, endfile = cutJacket(asset, event.group_id, size=30, isbw=False)
        guessDiff = 3
        text = '非人类曲绘'
        msgs.append(MessageSegment.image(f"file:///{file.absolute()}"))
    elif reg_group[0] == '听歌' or reg_group[1] == '4':
        musicid, musicname, asset = await getRandomMusic()
        file, endfile = cutMusic(asset, event.group_id, False)
        guessDiff = 4
        text = '听歌识曲'
        msgs.append(MessageSegment.record(f"file:///{file.absolute()}"))
    elif reg_group[0] == '倒放' or reg_group[1] == '5':
        musicid, musicname, asset = await getRandomMusic()
        file, endfile = cutMusic(asset, event.group_id, True)
        guessDiff = 5
        text = '倒放识曲'
        msgs.append(MessageSegment.record(f"file:///{file.absolute()}"))
    # elif reg_group[0] == '音效' or reg_group[1] == '6':
    #     musicid, musicname = await getRandomSE()
    #     file, endfile = cutSE(musicid, event.group_id)
    #     guessDiff = 6
    #     text = '纯音效识曲'
    #     msgs.append(MessageSegment.record(f"file:///{file.absolute()}"))
    elif reg_group[0] == '谱面' or reg_group[1] == '6':
        musicid, musicname = await getRandomChart()
        file, endfile = cutChart(musicid, event.group_id)
        guessDiff = 6
        text = '谱面识曲'
        msgs.append(MessageSegment.image(f"file:///{file.absolute()}"))
    else:
        await pjsk_guessmusic.finish(BUG_ERROR)
        return
    msgs.insert(0, image(b64=pic2b64(text2image(
        f'PJSK{text}竞猜 （随机裁切）\n艾特我+你的答案以参加猜曲（不要使用回复）\n'
        f'\n你有{guess_time}秒的时间回答\n可手动发送“结束猜曲”来结束猜曲'
    ))))
    for msg in msgs:
        await pjsk_guessmusic.send(msg)
    pjskguess[GUESS_MUSIC][event.group_id] = {
        'isgoing': True, 'diff': guessDiff, 'tips': None,
        'musicid': musicid, 'musicname': musicname,
        'userid': event.user_id, 'file': file, 'endfile': endfile
    }
    await asyncio.sleep(guess_time)
    await endgame(event.group_id, event.self_id, GUESS_MUSIC)
    # 采用scheduler有时会有严重的时间误差
    # delta = datetime.timedelta(seconds=guess_time)
    # trigger = DateTrigger(run_date=datetime.datetime.now() + delta)
    # scheduler.add_job(
    #     func=endgame,
    #     trigger=trigger,
    #     kwargs={'group_id':event.group_id, 'game_type': GUESS_MUSIC, 'self_id': event.self_id},
    #     # misfire_grace_time=5,
    # )


@pjsk_guessmap.handle()
async def _(event: GroupMessageEvent):
    global pjskguess
    if reply := pre_check(event.group_id):
        await pjsk_guesscard.finish(reply)
    msgs = []
    musicid, musicname = await getRandomChart()
    file, endfile = cutChart(musicid, event.group_id)
    guessDiff = 7
    msgs.append(image(b64=pic2b64(text2image(
        'PJSK谱面竞猜 （随机裁切）\n艾特我+你的答案以参加猜曲（不要使用回复）\n'
        f'\n你有{guess_time}秒的时间回答\n可手动发送“结束猜谱面”来结束猜曲'
    ))))
    msgs.append(MessageSegment.image(f"file:///{file.absolute()}"))
    for msg in msgs:
        await pjsk_guessmap.send(msg)
    pjskguess[GUESS_MUSIC][event.group_id] = {
        'isgoing': True, 'diff': guessDiff, 'tips': None,
        'musicid': musicid, 'musicname': musicname,
        'userid': event.user_id, 'file': file, 'endfile': endfile
    }
    await asyncio.sleep(guess_time)
    await endgame(event.group_id, event.self_id, GUESS_MUSIC)
    # 采用scheduler有时会有严重的时间误差
    # delta = datetime.timedelta(seconds=guess_time)
    # trigger = DateTrigger(run_date=datetime.datetime.now() + delta)
    # scheduler.add_job(
    #     func=endgame,
    #     trigger=trigger,
    #     kwargs={'group_id':event.group_id, 'game_type': GUESS_MUSIC, 'self_id': event.self_id},
    #     # misfire_grace_time=5,
    # )


@pjsk_gameover.handle()
async def _(event: GroupMessageEvent, state: T_State):
    game_type = state[PJSK_GUESS]
    text = '猜曲' if game_type == GUESS_MUSIC else '猜卡面'
    if pjskguess[game_type][event.group_id]['userid'] != event.user_id:
        await pjsk_guesstip.finish(f"您不是游戏发起者，不可以提前结束{text}", at_sender=True)
    else:
        await endgame(event.group_id, event.self_id, game_type, advanceover=True)


@pjsk_guesstip.handle()
async def _(event: GroupMessageEvent, state: T_State):
    global pjskguess
    game_type = state[PJSK_GUESS]
    if event.user_id != pjskguess[game_type][event.group_id]['userid']:
        await pjsk_guesstip.finish("您不是游戏发起者，不可以使用提示功能", at_sender=True)
    voidflag = False
    if pjskguess[game_type][event.group_id]['tips'] is None:
        pjskguess[game_type][event.group_id]['tips'] = []
        voidflag = True
    alltips = pjskguess[game_type][event.group_id]['tips']
    # 猜卡面：学校0、性别1、爱好2、团队信息3、卡面信息(卡面属性4、卡面是否特训5、卡面稀有度6)
    if game_type == GUESS_CARD:
        cardid = pjskguess[GUESS_CARD][event.group_id]['cardid']
        charaid = pjskguess[GUESS_CARD][event.group_id]['charaid']
        # 若未提示过，初始化字段
        if voidflag:
            for _t in random.sample(range(4), k=max_tips_count):
                if _t == 0:
                    content = '没有提示'
                elif _t == 1:
                    content = '没有提示'
                elif _t == 2:
                    content = '没有提示'
                else:
                    content = '没有提示'
                alltips.append(content)
    # 猜曲：难度等级0、演唱者1、歌名提示2
    else:
        musicid = pjskguess[GUESS_MUSIC][event.group_id]['musicid']
        # 若未提示过，初始化字段
        if voidflag:
            for _t in random.sample(range(3), k=max_tips_count):
                if _t == 0:
                    content = '没有提示'
                elif _t == 1:
                    content = '没有提示'
                elif _t == 2:
                    content = '没有提示'
                else:
                    content = '没有提示'
                alltips.append(content)
    # 选择任意一种可用字段发送
    if len(alltips) > 0:
        tip = alltips.pop(random.randint(0, len(alltips)-1))
        await pjsk_guesstip.finish(f'提示：{tip}哦！\n剩余提示次数：({len(alltips)}/{max_tips_count})')
    # 已到最大提示次数
    else:
        await pjsk_guesstip.finish(f'已经提示过{max_tips_count}次了，不会再提示了！')


@pjsk_guessrank.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    game_type = GUESS_CARD if reg_group[1] == '猜卡面' else GUESS_MUSIC
    if not reg_group[0]:
        guess_diff = None
        text = '合计'
    elif reg_group[0] == '正常':
        guess_diff = 1
        text = '正常'
    elif reg_group[0] == '阴间':
        guess_diff = 2
        text = '阴间'
    elif reg_group[0] == '非人类':
        guess_diff = 3
        text = '非人类'
    elif reg_group[0] == '听歌':
        guess_diff = 4
        text = '听歌'
    elif reg_group[0] == '倒放':
        guess_diff = 5
        text = '倒放'
    elif reg_group[0] == '谱面':
        guess_diff = 6
        text = '谱面'
    else:
        await pjsk_guessrank.finish(BUG_ERROR)
        return
    if reg_group[1] == '猜谱面':
        guess_diff = 6
    if str(reg_group[2]).isdigit():
        total_count = int(reg_group[2]) if 10 <= int(reg_group[2]) <= 50 else 50
    else:
        total_count = 10
    if game_type == GUESS_CARD and guess_diff > 3:
        await pjsk_guessrank.finish("没有这种类型的排行榜哦！")
    users, ranks = await PjskGuessRank.get_rank(event.group_id, game_type, guess_diff)
    if len(users) == 0:
        await pjsk_guessrank.finish("当前类型排行榜尚无人上榜哦")
    _type = '猜曲' if game_type == GUESS_MUSIC else '猜卡面'
    try:
        pic = await init_rank(
            f"{text}{_type}排行榜", users, ranks, event.group_id,
            total_count=total_count, limit_count=50, save_key=f"g{event.group_id}_{total_count}_pjskguess"
        )
        await pjsk_guessrank.finish(image(b64=pic.pic2bs4()))
    except:
        await pjsk_guessrank.finish(BUG_ERROR)


async def endgame(
    group_id: int,
    self_id: int,
    game_type: str,
    user_qq: Optional[int] = None,
    gameover: bool = False,
    advanceover: bool = False,
    plugin_name: Optional[str] = None,
    event: Optional[GroupMessageEvent] = None
):
    global pjskguess
    try:
        # 判断游戏是否进行中
        if pjskguess[game_type][group_id].get('isgoing', False):
            msgs = []
            file = pjskguess[game_type][group_id]['file']
            endfile = pjskguess[game_type][group_id]['endfile']
            # 收到正确回答，提前结束游戏
            if gameover:
                qq = pjskguess[game_type][group_id]['userid']
                if pjskguess[game_type][group_id]['tips'] is None:
                    tipcount = 0
                else:
                    tipcount = max_tips_count - len(pjskguess[game_type][group_id]['tips'])
                diff = pjskguess[game_type][group_id]['diff']
                # 针对猜曲
                if game_type == GUESS_MUSIC:
                    musicname = pjskguess[game_type][group_id]['musicname']
                    # 结算金币 按难度决定基础奖励
                    rdgold = random.randint(0, {1: 3, 2: 5, 3: 10, 4: 3, 5: 10, 6: 10}.get(diff))
                    gold = {1: 10, 2: 15, 3: 30, 4: 10, 5: 30, 6: 30}.get(diff) + rdgold
                    # 游戏中使用了提示功能，奖励每次扣除25%
                    gold = math.ceil(gold - tipcount * gold // 4)
                    # 游戏发起者以外的人回答正确，0.9倍率
                    if user_qq and user_qq != pjskguess[game_type][group_id]['userid']:
                        qq = user_qq
                        gold = math.ceil(0.9 * gold)
                    if diff in [1, 2, 3, 6]:
                        msgs.append(f"正确答案：{musicname}")
                        msgs.append(MessageSegment.image(f'file:///{endfile.absolute()}'))
                    else:
                        msgs.append(f"正确答案：{musicname}")
                        msgs.append(MessageSegment.record(f'file:///{endfile.absolute()}'))
                # 针对猜卡面
                else:
                    cardname = pjskguess[game_type][group_id]['cardname']
                    charaname = pjskguess[game_type][group_id]['charaname']
                    # 结算金币 按难度决定基础奖励
                    rdgold = random.randint(0, {1: 3, 2: 5, 3: 10}.get(diff))
                    gold = {1: 10, 2: 15, 3: 30}.get(diff) + rdgold
                    # 游戏中使用了提示功能，奖励每次扣除25%
                    gold = math.ceil(gold - tipcount * gold // 4)
                    # 游戏发起者以外的人回答正确，0.9倍率
                    if user_qq and user_qq != pjskguess[game_type][group_id]['userid']:
                        qq = user_qq
                        gold = math.ceil(0.9 * gold)
                    msgs.append(f"正确答案：{cardname} - {charaname}")
                    msgs.append(MessageSegment.image(f'file:///{endfile.absolute()}'))
                # 记录进数据库
                addflag = await PjskGuessRank.add_count(qq, group_id, game_type, int(diff))
                if addflag:
                    msgs[0] = at(qq) + f"您猜对了，奖励{gold}金币！\n" + msgs[0]
                    await BagUser.add_gold(qq, group_id, gold)
                else:
                    msgs[0] = at(qq) + f"您猜对了，但是已达今日游戏获取金币上限，并没有奖励！\n" + msgs[0]
            # 时间到自然结束游戏 或 提前结束
            else:
                _over = '提前结束' if advanceover else '时间到'
                # 针对猜曲
                if game_type == GUESS_MUSIC:
                    musicname = pjskguess[game_type][group_id]['musicname']
                    if pjskguess[game_type][group_id]['diff'] in [1, 2, 3, 6]:
                        msgs.append(f"{_over}，正确答案：{musicname}")
                        msgs.append(MessageSegment.image(f'file:///{endfile.absolute()}'))
                    else:
                        msgs.append(f"{_over}，正确答案：{musicname}")
                        msgs.append(MessageSegment.record(f'file:///{endfile.absolute()}'))
                # 针对猜卡面
                elif game_type == GUESS_CARD:
                    cardname = pjskguess[game_type][group_id]['cardname']
                    msgs.append(f"{_over}，正确答案：{cardname}")
                    msgs.append(MessageSegment.image(f'file:///{endfile.absolute()}'))
            pjskguess[game_type][group_id].clear()
            # 发送信息
            bot: Bot = get_bot(str(self_id))
            try:
                for msg in msgs:
                    await bot.send_msg(message_type='group', group_id=group_id, message=msg)
            except:
                pass
            if file and file.exists():
                file.unlink()
            if endfile and endfile.exists():
                endfile.unlink()
            if not(plugin_name is None or event is None):
                access_count(plugin_name, event)
                access_cd(plugin_name, event)
    except KeyError:
        pass
    except Exception as e:
        logger.warning(f"pjsk猜曲结算环节出错，Error:{e}")
