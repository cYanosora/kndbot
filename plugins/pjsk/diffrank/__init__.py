import os
import time
from typing import Tuple, Any
from PIL import Image, ImageDraw, ImageFont
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP
from nonebot.params import RegexGroup
from configs.path_config import FONT_PATH
from utils.imageutils import pic2b64
from utils.message_builder import image
from .._config import data_path
try:
    import ujson as json
except:
    import json

__plugin_name__ = "难度排行"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤难度排行，移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    限制每个群1分钟只能查询2次
    
    定数必须指定，难度默认为ma，不带参数ap、fc时为综合排行
    指令：
        难度排行   [定数] [难度]
        ap难度排行 [定数] [难度]
        fc难度排行 [定数] [难度]
    示例：
        难度排行   26
        ap难度排行 27 ma
        fc难度排行 28 ex
    数据来源：
        pjsekai.moe
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["难度排行", "烧烤相关", "uni移植"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# pjsk热度排行
pjsk_hotrank = on_regex('^(.*)难度排行(.*)', permission=GROUP, priority=5, block=True)


@pjsk_hotrank.handle()
async def _(reg_group: Tuple[Any, ...] = RegexGroup()):
    fcap = {'ap': 2, 'fc': 1}.get(reg_group[0].strip(), 0)
    tmp_arg = reg_group[1].strip().split()
    if len(tmp_arg) == 2:
        level = int(tmp_arg[0]) if tmp_arg[0].isdigit() else 0
        difficulty = tmp_arg[1]
        difficulty_dict = {
            'ma': 'master', 'master': 'master',
            'ex': 'expert', 'expert': 'expert',
            'hd': 'hard', 'hard': 'hard',
            'nm': 'normal', 'normal': 'normal',
            'ez': 'eazy', 'eazy': 'eazy'
        }
        difficulty = difficulty_dict.get(difficulty, None)
    elif len(tmp_arg) == 1:
        level, difficulty = int(tmp_arg[0]) if tmp_arg[0].strip().isdigit() else 0, 'master'
    else:
        level, difficulty = 0, None
    if not level or not difficulty:
        await pjsk_hotrank.finish(
            '参数错误，指令：难度排行 定数 难度\n'
            '难度支持的输入: easy/ez, normal/nm, hard/hd, expert/ex, master/ma，如：难度排行 28 expert'
        )
    target = []
    with open(data_path / r'realtime/musicDifficulties.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(data_path / r'realtime/musics.json', 'r', encoding='utf-8') as f:
        musics = json.load(f)
    for i in data:
        if i['playLevel'] == level and i['musicDifficulty'] == difficulty:
            target.append(i)
    for i in range(0, len(target)):
        try:
            target[i]['playLevelAdjust']
        except KeyError:
            target[i]['playLevelAdjust'] = 0
            target[i]['fullComboAdjust'] = 0
            target[i]['fullPerfectAdjust'] = 0
    if fcap == 0:
        title = f'{difficulty.upper()} {level}难度排行（仅供参考）'
        target.sort(key=lambda x: x["playLevelAdjust"], reverse=True)
    elif fcap == 1:
        title = f'{difficulty.upper()} {level}FC难度排行（仅供参考）'
        target.sort(key=lambda x: x["fullComboAdjust"], reverse=True)
    else:
        title = f'{difficulty.upper()} {level}AP难度排行（仅供参考）'
        target.sort(key=lambda x: x["fullPerfectAdjust"], reverse=True)
    text = ''
    musictitle = ''
    for i in target:
        for j in musics:
            if j['id'] == i['musicId']:
                musictitle = j['title']
                break
        if fcap == 0:
            text += f"{musictitle} ({round(i['playLevel'] + i['playLevelAdjust'], 1)})\n"
        elif fcap == 1:
            text += f"{musictitle} ({round(i['playLevel'] + i['fullComboAdjust'], 1)})\n"
        else:
            text += f"{musictitle} ({round(i['playLevel'] + i['fullPerfectAdjust'], 1)})\n"
    if not text:
        await pjsk_hotrank.finish('请检查定数是否正确！', at_sender=True)
    IMG_SIZE = (500, int(100 + text.count('\n') * 31.5))
    img = Image.new('RGB', IMG_SIZE, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 22)
    draw.text((20, 15), title, '#000000', font, spacing=10)
    font = ImageFont.truetype(str(FONT_PATH / 'FOT-RodinNTLGPro-DB.ttf'), 22)
    draw.text((20, 55), text, '#000000', font, spacing=10)
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 15)
    updatetime = time.localtime(os.path.getmtime(data_path / "realtime/musicDifficulties.json"))
    draw.text((20, int(45 + text.count('\n') * 31.5)), '数据来源：https://profile.pjsekai.moe/\nUpdated in '
              + time.strftime("%Y-%m-%d %H:%M:%S", updatetime), '#000000', font)

    await pjsk_hotrank.finish(image(b64=pic2b64(img)))