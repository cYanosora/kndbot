import re
from nonebot import require
from nonebot.rule import Rule
from nonebot.typing import T_State, T_RuleChecker
from nonebot.params import Depends
from nonebot.adapters.onebot.v11 import GroupMessageEvent
try:
    require('image_management')
    require('pjsk_images')
    from plugins.image_management.pjsk_images.pjsk_db_source import PjskAlias
    search_flag = True
except:
    search_flag = False
    pass


def checkRule() -> T_RuleChecker:
    async def checker(event: GroupMessageEvent, state: T_State) -> bool:
        msg = event.get_plaintext().strip()
        matched = re.match(rf"(.*?)说(中文|日文)?(.*)", msg)
        if not matched:
            return False
        name, type, text = matched.groups()
        name, text = name.strip(), text.strip()
        if event.is_tome() and not name:
            name = 'knd'
        if not name or not text:
            return False
        name_ls = [
            'ick', 'saki', 'hnm', 'shiho',
            'mnr', 'hrk', 'airi', 'szk',
            'khn', 'an', 'akt', 'toya',
            'tks', 'emu', 'nene', 'rui',
            'knd', 'mfy', 'ena', 'mzk'
        ]
        # 使用烧烤图库
        if name not in name_ls and search_flag:
            name = await PjskAlias.query_name(name)
            if not name or name not in name_ls:
                return False
        type = type if type is not None else '日文'
        state['vits_name'] = name
        state['vits_type'] = type
        state['vits_text'] = text
        return True
    return Rule(checker)


def RegexArg(key: str):
    async def dependency(state: T_State):
        return state[f'vits_{key}']
    return Depends(dependency)