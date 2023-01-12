import json
import os
import re
from hashlib import md5
from typing import Tuple

from nonebot import on_command, require
from nonebot.adapters.onebot.v11 import GROUP, Message
from nonebot.params import CommandArg, Command
from .._config import data_path, BUG_ERROR
from .._utils import currentevent
from .._event_utils import drawevent, draweventall
from .._models import EventInfo
from utils.message_builder import image

require('image_management')
require('pjsk_images')
from plugins.image_management.pjsk_images.pjsk_db_source import PjskAlias

__plugin_name__ = "活动查询/event"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤活动信息，移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    限制每个群半分钟只能查询2次
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
__plugin_cd_limit__ = {"cd": 30, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


eventinfo = on_command('event', permission=GROUP, priority=5, block=True)

findevent = on_command(
    'findevent',
    aliases={"查活动", "查询活动", "活动图鉴", "活动总览", "活动手册", "活动列表"},
    permission=GROUP,
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


@findevent.handle()
async def _findevent(cmd: Tuple = Command(),arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if args.isdigit():
        await _eventinfo(arg)
        return
    else:
        args = args.split()
    event_type = 'all'
    event_attr = 'all'
    event_charas_id = []
    for i in args:
        # 是否为活动类型
        if _ := {
            '普活': 'marathon', '马拉松': 'marathon', 'marathon': 'marathon',
            '5v5': 'cheerful_carnival', 'cheerful_carnival': 'cheerful_carnival'
        }.get(i):
            event_type = _
        # 是否为活动属性
        elif _ := {
            '蓝星':'cool', '紫月':'mysterious', '橙心':'happy', '粉花':'cute', '绿草':'pure',
            '蓝': 'cool', '紫': 'mysterious', '橙': 'happy', '粉': 'cute', '绿': 'pure',
            '星': 'cool', '月': 'mysterious', '心': 'happy', '花': 'cute', '草': 'pure',
            'cool': 'cool', 'mysterious': 'mysterious', 'happy': 'happy', 'cute': 'cute', 'pure': 'pure',
        }.get(i):
            event_attr = _
        # 是否为组合（并不包含vs角色）
        elif _ := {
            'ln': [1,2,3,4], 'mmj': [5,6,7,8],'vbs': [9,10,11,12],'ws': [13,14,15,16],'25时': [17,18,19,20],
        }.get(i):
            event_charas_id.extend(_)
        # 是否为角色
        else:
            # 是否是带附属组合的vs角色
            for unit in ['ln','mmj','vbs','ws','25时']:
                if i.startswith(unit):
                    unit_dict = {
                        'ln': 'light_sound', 'mmj': 'idol', 'vbs': 'street', 'ws': 'theme_park', '25时': 'school_refusal'
                    }
                    chara_dict = {'miku':21,'rin':22,'len':23,'luka':24,'meiko':25,'kaito':26}
                    alias = i[len(unit):]
                    if alias not in chara_dict.keys():
                        alias = await PjskAlias.query_name(i[len(unit):])
                    if alias:
                        event_charas_id.append((chara_dict[alias],unit_dict[unit]))
                        break
            # sekai角色、无附属组合的vs角色
            else:
                chara_dict = {
                    'ick': 1, 'saki': 2, 'hnm': 3, 'shiho': 4,
                    'mnr': 5, 'hrk': 6, 'airi': 7, 'szk': 8,
                    'khn': 9, 'an': 10, 'akt': 11, 'toya': 12,
                    'tks': 13, 'emu': 14, 'nene': 15, 'rui': 16,
                    'knd': 17, 'mfy': 18, 'ena': 19, 'mzk': 20,
                    'miku': 21, 'rin': 22, 'len': 23, 'luka': 24, 'meiko': 25, 'kaito': 26
                }
                alias = i
                if alias not in chara_dict.keys():
                    alias = await PjskAlias.query_name(i)
                if alias:
                    event_charas_id.append(chara_dict[alias])
    # 携带参数但是参数不合规范
    if args and event_type == 'all' and event_attr == 'all' and not event_charas_id:
        tip_path = data_path / 'pics/findevent_tips.jpg'
        await findevent.finish(image(tip_path))
    # 没有参数但是指令不是活动图鉴
    elif not args and cmd[0] not in ["活动列表", "活动图鉴", "活动总览", "活动手册"]:
        tip_path = data_path / 'pics/findevent_tips.jpg'
        await findevent.finish(image(tip_path))
    # 检查本地活动图鉴是否需要更新
    with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
        events = json.load(f)
    count = len(events)
    path = data_path / 'findevent'
    path.mkdir(parents=True, exist_ok=True)
    # 图片路径格式
    charas_id_name = event_charas_id.copy()
    for i in range(len(event_charas_id)):
        if isinstance(event_charas_id[i], tuple):
            charaid = event_charas_id[i][0] + ([
                 'light_sound','idol','street','theme_park','school_refusal'
            ].index(event_charas_id[i][1])+1)*6
            charas_id_name[i] = charaid
    charas_id_name.sort()
    save_file_prefix = md5(f'{event_type}{event_attr}{charas_id_name}'.encode()).hexdigest()
    save_path = path / f'{save_file_prefix}-{count}.jpg'
    if save_path.exists():
        await findevent.finish(image(save_path))
    else:
        # 开始生成新活动图鉴
        isContainAllCharasId = True     # 活动出卡是否需要包含所有角色id
        try:
            pic = await draweventall(event_type, event_attr, event_charas_id, isContainAllCharasId, events)
        except:
            await findevent.finish(BUG_ERROR)
        else:
            if pic:
                pic = pic.convert('RGB')
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
