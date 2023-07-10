import json
import os
import re
from hashlib import md5
from typing import Tuple, List
from nonebot import on_command, require
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg, Command
from .._config import data_path
from .._utils import currentevent
from .._event_utils import drawevent, draweventall
from .._models import EventInfo
from utils.message_builder import image

require('image_management')
require('pjsk_images')
from ...image_management.pjsk_images.pjsk_db_source import PjskAlias

__plugin_name__ = "活动查询/event"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤活动信息
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询4次
    指令：
        event ?[活动id]                     : 查看对应活动id的活动信息，无参数时默认为当前活动
        findevent/查活动/查询活动 [关键字]     : 通过关键字筛选活动概要信息
        findevent/查活动/查询活动             : 直接获取上方指令中对于[关键字]的说明
    数据来源：
        pjsek.ai
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["event", "烧烤相关", "uni移植", "活动查询"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 4, "rst": "别急，等[cd]秒后再用！", "limit_type": "user"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


eventinfo = on_command('event', priority=5, block=True)

findevent = on_command(
    'findevent',
    aliases={"查活动", "查询活动", "活动图鉴", "活动总览", "活动手册", "活动列表"},
    priority=4,
    block=True
)


@eventinfo.handle()
async def _eventinfo(arg: Message = CommandArg()):
    eventid = re.sub(r'\D', "", arg.extract_plain_text().strip())
    if not eventid:
        eventid = currentevent()['id']
    else:
        eventid = int(eventid)
    # 检查本地是否已经有活动图片
    path = data_path / 'eventinfo'
    path.mkdir(parents=True, exist_ok=True)
    save_path = path / f'event_{eventid}.jpg'
    if save_path.exists():
        await findevent.finish(image(save_path))
    else:
        eventinfo = EventInfo()
        if eventinfo.getevent(eventid):
            pic = await drawevent(eventinfo)
            pic.save(save_path)
            await findevent.finish(image(save_path))
        else:
            await findevent.finish("未找到活动或生成失败")


async def event_argparse(args: List = None):
    if not args:
        args = []
    event_type = None            # 活动类型
    event_attr = None            # 活动属性
    event_units_name = []        # 活动组合名称
    event_charas_id = []         # 活动出卡角色id
    isEqualAllUnits = True     # 活动组合是否需要完全等同所有组合名称
    isContainAllCharasId = True  # 活动出卡是否需要包含所有角色id
    islegal = True               # 参数是否合法
    isTeamEvent = None          # 是否指定箱活
    unit_dict = {
        'ln': 'light_sound', 'mmj': 'idol', 'vbs': 'street', 'ws': 'theme_park', '25h': 'school_refusal',
    }
    team_dict = {
        '箱活': True, '团队活': True, '混活': False, '团外活': False
    }
    event_type_dict = {
        '普活': 'marathon', '马拉松': 'marathon', 'marathon': 'marathon',
        '5v5': 'cheerful_carnival', 'cheerful_carnival': 'cheerful_carnival'
    }
    event_attr_dict = {
        '蓝星': 'cool', '紫月': 'mysterious', '橙心': 'happy', '黄心': 'happy', '粉花': 'cute', '绿草': 'pure',
        '蓝': 'cool', '紫': 'mysterious', '橙': 'happy', '黄': 'happy', '粉': 'cute', '绿': 'pure',
        '星': 'cool', '月': 'mysterious', '心': 'happy', '花': 'cute', '草': 'pure',
        'cool': 'cool', 'mysterious': 'mysterious', 'happy': 'happy', 'cute': 'cute', 'pure': 'pure',
    }
    chara_dict = {
        'ick': 1, 'saki': 2, 'hnm': 3, 'shiho': 4,
        'mnr': 5, 'hrk': 6, 'airi': 7, 'szk': 8,
        'khn': 9, 'an': 10, 'akt': 11, 'toya': 12,
        'tks': 13, 'emu': 14, 'nene': 15, 'rui': 16,
        'knd': 17, 'mfy': 18, 'ena': 19, 'mzk': 20,
        'miku': 21, 'rin': 22, 'len': 23, 'luka': 24, 'meiko': 25, 'kaito': 26
    }
    chara2unit_dict = {
        'light_sound': [1,2,3,4],
        'idol': [5,6,7,8],
        'street': [9,10,11,12],
        'theme_park': [13,14,15,16],
        'school_refusal': [17,18,19,20]
    }
    for arg in args:
        # 参数是否指定了箱活或混活
        if arg in team_dict.keys():
            isTeamEvent = team_dict[arg]
            continue
        # 参数是否为活动类型，只能指定一种
        if _ := event_type_dict.get(arg):
            if event_type:
                islegal = False
                break
            else:
                event_type = _
                continue
        # 参数是否为活动属性，只能指定一种
        if _ := event_attr_dict.get(arg):
            if event_attr:
                islegal = False
                break
            else:
                event_attr = _
                continue
        # 参数是否为组合缩写(指定一个时为箱活，指定多个时为混活)
        if _ := unit_dict.get(arg):
            event_units_name.append(_)
            continue
        # 参数是否为组合缩写(对参数中含"混"、"加成"的额外再判定一次)
        # 末尾为"混"、"加成"，说明需要筛选带此组合任意角色玩的混活
        unit_rule = "|".join(unit_dict.keys())
        if match := re.match(rf'^({unit_rule})(?:混|加成)$', arg):
            try:
                event_units_name.append(unit_dict[match.group(1)])
            except KeyError:
                islegal = False
                break
            else:
                isEqualAllUnits = False
                continue
        # 中间为"混"
        if match := re.match(rf'^({unit_rule})混({unit_rule}).*$', arg):
            try:
                event_units_name.extend(unit_dict[j] for j in match.group().split('混'))
                continue
            except KeyError:
                islegal = False
                break
        # 参数是否是带附属组合的vs角色
        if match := re.match(rf"^({unit_rule})(.+)", arg):
            unit = match.group(1)
            alias = match.group(2)
            if alias not in [i for i in chara_dict.keys() if chara_dict[i] > 20]:
                alias = await PjskAlias.query_name(alias)
            if alias and chara_dict[alias] > 20:
                event_charas_id.append((chara_dict[alias], unit_dict[unit]))
                continue
            else:
                islegal = False
                break
        # 以上判定均无果，则认定为sekai角色或无附属组合的vs角色
        alias = arg
        if alias not in chara_dict.keys():
            alias = await PjskAlias.query_name(arg)
        if alias and chara_dict.get(alias):
            event_charas_id.append(chara_dict[alias])
        # 参数仍无法识别
        else:
            islegal = False
            break

    for i in event_charas_id:
        if isinstance(i, tuple):
            unit = i[1]
        elif i <= 20:
            unit = [x for x in chara2unit_dict.keys() if i in chara2unit_dict[x]][0]
        else:
            continue
        if len(event_units_name) != 0 and unit not in event_units_name:
            event_units_name.append(unit)
            isEqualAllUnits = False
    # 箱活标志只能与活动类型、活动属性搭配
    if isTeamEvent is not None and (len(event_units_name)>0 or len(event_charas_id)>0):
        islegal = False
    return {
        'event_type': event_type, 'event_attr': event_attr,
        'event_units_name': list(set(event_units_name)), 'event_charas_id': list(set(event_charas_id)),
        'islegal': islegal, 'isTeamEvent': isTeamEvent,
        'isEqualAllUnits': isEqualAllUnits, 'isContainAllCharasId': isContainAllCharasId

    }


@findevent.handle()
async def _findevent(cmd: Tuple = Command(),arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if args.isdigit():
        await _eventinfo(arg)
        return
    else:
        args = args.split()
    params = await event_argparse(args)
    if not params['islegal']:
        tip_path = data_path / 'pics/findevent_tips.jpg'
        await findevent.finish(image(tip_path))
    # 没有参数但是指令不是活动图鉴
    elif not args and cmd[0] not in ["活动列表", "活动图鉴", "活动总览", "活动手册"]:
        return
    # 检查本地活动图鉴是否需要更新
    with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    count = len(events)
    path = data_path / 'findevent'
    path.mkdir(parents=True, exist_ok=True)
    # 图片路径格式
    # 备份
    _event_charas_id = params['event_charas_id'].copy()
    _event_units_name = params['event_units_name'].copy()
    charas_id_name = params['event_charas_id']
    params['event_units_name'].sort()
    for i in range(len(_event_charas_id)):
        if isinstance(_event_charas_id[i], tuple):
            _charaid = _event_charas_id[i][0] + ([
                 'light_sound','idol','street','theme_park','school_refusal'
            ].index(_event_charas_id[i][1])+1)*6
            charas_id_name[i] = _charaid
    charas_id_name.sort()
    save_file_prefix = md5(''.join(str(params.values())).encode()).hexdigest()
    save_path = path / f'{save_file_prefix}-{count}.jpg'
    # 还原
    params['event_charas_id'] = _event_charas_id
    params['event_units_name'] = _event_units_name

    if save_path.exists():
        await findevent.finish(image(save_path))
    else:
        # 开始生成新活动图鉴
        try:
            pic = await draweventall(events=events, **params)
        except Exception as e:
            raise e
        else:
            if pic:
                pic = pic.convert('RGB')
                pic.show()
                pic.save(save_path, quality=70)
                await findevent.finish(image(save_path))
            else:
                tip_path = data_path / 'pics/findevent_tips.jpg'
                await findevent.finish(image(tip_path))
        finally:
            # 因为需要更新，所以清除所有旧活动图鉴
            for file in os.listdir(path):
                if not file.split('.')[0].endswith(str(count)):
                    (path / file).unlink()
