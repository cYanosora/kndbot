import os
import time
from typing import Tuple, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent
from nonebot.params import RegexGroup
from configs.path_config import FONT_PATH
from utils.imageutils import pic2b64
from utils.message_builder import image
from .._autoask import pjsk_update_manager
from .._config import data_path
from .._models import PjskBind, UserProfile
from .._utils import generatehonor

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
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    if not reg_group[0] and not reg_group[1]:
        level = 0
        fcap = 2
        difficulty = 'master'
    else:
        fcap = {'ap': 2, 'fc': 1}.get(reg_group[0].strip(), 0)
        tmp_arg = reg_group[1].strip()
        difficulty_dict = {
            'ma': 'master', 'master': 'master',
            'ex': 'expert', 'expert': 'expert',
            'hd': 'hard', 'hard': 'hard',
            'nm': 'normal', 'normal': 'normal',
            'ez': 'eazy', 'eazy': 'eazy'
        }
        for diff in difficulty_dict.keys():
            if tmp_arg.endswith(diff):
                difficulty = difficulty_dict[diff]
                level = tmp_arg.replace(diff, '').strip()
                break
            elif tmp_arg.startswith(diff):
                difficulty = difficulty_dict[diff]
                level = tmp_arg.replace(diff, '').strip()
                break
        else:
            difficulty = 'master'
            level = tmp_arg.strip()
        level = int(level) if level.isdigit() else 0
        if not tmp_arg.strip() and level == 0:
            await pjsk_hotrank.finish(
                '参数错误，指令：难度排行 定数 难度\n'
                '难度支持的输入: easy/ez, normal/nm, hard/hd, expert/ex, master/ma，如：难度排行 28 expert'
            )
    # 生成图片
    target = []
    with open(data_path / 'realtime/musicDifficulties.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    for i in data:
        if (i['playLevel'] == level if level != 0 else True) and i['musicDifficulty'] == difficulty:
            try:
                i['playLevelAdjust']
                target.append(i)
            except KeyError:
                pass

    if fcap == 0:
        title = f'{difficulty.upper()} {level if level != 0 else ""} 难度表（仅供参考）'
        playLevelKey = "playLevelAdjust"
    elif fcap == 1:
        title = f'{difficulty.upper()} {level if level != 0 else ""} FC难度表（仅供参考）'
        playLevelKey = "fullComboAdjust"
    else:
        title = f'{difficulty.upper()} {level if level != 0 else ""} AP难度表（仅供参考）'
        playLevelKey = "fullPerfectAdjust"

    target.sort(key=lambda x: x['playLevel'] + x[playLevelKey], reverse=True)
    musicData = {}
    for music in target:
        levelRound = str(round(music['playLevel'] + music[playLevelKey], 1))
        try:
            musicData[levelRound].append(music['musicId'])
        except KeyError:
            musicData[levelRound] = [music['musicId']]
    profile = None
    error = False
    userid, isprivate = await PjskBind.get_user_bind(event.user_id)
    if userid and not isprivate:
        profile = UserProfile()
        try:
            await profile.getprofile(userid=userid)
            rankPic = await singleLevelRankPic(musicData, difficulty, profile.musicResult, oneRowCount=None if level != 0 else 5)
        except:
            rankPic = await singleLevelRankPic(musicData, difficulty, oneRowCount=None if level != 0 else 5)
            error = True
    else:
        rankPic = await singleLevelRankPic(musicData, difficulty, oneRowCount=None if level != 0 else 5)
    rankPic = rankPic.resize((int(rankPic.size[0] / 1.8), int(rankPic.size[1] / 1.8)))
    pic = Image.new("RGBA", (rankPic.size[0] + 20 if rankPic.size[0] > 520 else 600, rankPic.size[1] + 430), (205, 255, 255, 255))
    bg = Image.open(data_path / 'pics/findevent.png')
    picRatio = pic.size[0] / pic.size[1]
    bgRatio = bg.size[0] / bg.size[1]
    if picRatio > bgRatio:
        bg = bg.resize((pic.size[0], int(pic.size[0] / bgRatio)))
    else:
        bg = bg.resize((int(pic.size[1] * bgRatio), pic.size[1]))

    pic.paste(bg, (0, 0))
    userdataimg = Image.open(data_path / 'pics/userdata.png')
    r,g,b,mask = userdataimg.split()
    pic.paste(userdataimg, (0, 0), mask)
    draw = ImageDraw.Draw(pic)
    if error:
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 35)
        draw.text((215, 65), '获取个人数据发生错误', fill=(0, 0, 0), font=font_style)
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 15)
        draw.text((218, 114), '可能由于bot网不好或者游戏正在维护', fill=(0, 0, 0), font=font_style)
    elif profile is not None:
        with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
            cards = json.load(f)
        try:
            assetbundleName = ''
            for i in cards:
                if i['id'] == profile.userDecks[0]:
                    assetbundleName = i['assetbundleName']
            if profile.special_training[0]:
                cardimg = await pjsk_update_manager.get_asset(
                    f'startapp/thumbnail/chara', f'{assetbundleName}_after_training.png'
                )
            else:
                cardimg = await pjsk_update_manager.get_asset(
                    f'startapp/thumbnail/chara', f'{assetbundleName}_normal.png'
                )

            cardimg = cardimg.resize((116, 116))
            r, g, b, mask = cardimg.split()
            pic.paste(cardimg, (68, 70), mask)
        except FileNotFoundError:
            pass
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 35)
        draw.text((215, 65), profile.name, fill=(0, 0, 0), font=font_style)
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 15)
        draw.text((218, 114), '发送"不给看"可隐藏打歌数据', fill=(0, 0, 0), font=font_style)
        font_style = ImageFont.truetype(str(FONT_PATH / "FOT-RodinNTLGPro-DB.ttf"), 28)
        draw.text((314, 150), str(profile.rank), fill=(255, 255, 255), font=font_style)

        for i in profile.userProfileHonors:
            if i['seq'] == 1:
                try:
                    honorpic = await generatehonor(i, True)
                    honorpic = honorpic.resize((226, 48))
                    r, g, b, mask = honorpic.split()
                    pic.paste(honorpic, (59, 206), mask)
                except:
                    pass

        for i in profile.userProfileHonors:
            if i['seq'] == 2:
                try:
                    honorpic = await generatehonor(i, False)
                    honorpic = honorpic.resize((107, 48))
                    r, g, b, mask = honorpic.split()
                    pic.paste(honorpic, (290, 206), mask)
                except:
                    pass

        for i in profile.userProfileHonors:
            if i['seq'] == 3:
                try:
                    honorpic = await generatehonor(i, False)
                    honorpic = honorpic.resize((107, 48))
                    r, g, b, mask = honorpic.split()
                    pic.paste(honorpic, (403, 206), mask)
                except:
                    pass
    elif isprivate:
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 35)
        draw.text((215, 65), '成绩已隐藏', fill=(0, 0, 0), font=font_style)
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 15)
        draw.text((218, 114), '发送"给看"可查看歌曲成绩', fill=(0, 0, 0), font=font_style)
    else:
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 35)
        draw.text((215, 65), '未绑定日服账号', fill=(0, 0, 0), font=font_style)
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 15)
        draw.text((218, 114), '绑定后可查看歌曲成绩', fill=(0, 0, 0), font=font_style)

    font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 30)
    draw.text((65, 264), title, fill=(0, 0, 0), font=font_style)

    r, g, b, mask = rankPic.split()
    pic.paste(rankPic, (40, 320), mask)

    updatetime = time.localtime(os.path.getmtime(data_path / r"realtime/musicDifficulties.json"))
    font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 16)
    draw.text((50, pic.size[1] - 70), '定数来源：https://profile.pjsekai.moe/   ※定数非官方\n', fill='#00CCBB',
              font=font_style)
    draw.text((50, pic.size[1] - 40), f'Updated in {time.strftime("%Y-%m-%d %H:%M:%S", updatetime)}        '
                                      '※定数每次统计时可能会改变', fill='#00CCBB', font=font_style)
    pic = pic.convert("RGB")
    await pjsk_hotrank.finish(image(b64=pic2b64(pic)))


async def singleLevelRankPic(musicData, difficulty, musicResult=None, oneRowCount=None):
    diff = {
        'easy': 0,
        'normal': 1,
        'hard': 2,
        'expert': 3,
        'master': 4
    }
    color = {
        'master': (187, 51, 238),
        'expert': (238, 67, 102),
        'hard': (254, 170, 0),
        'normal': (51, 187, 238),
        'easy': (102, 221, 17),
    }
    iconName = {
        0: 'icon_notClear.png',
        1: 'icon_clear.png',
        2: 'icon_fullCombo.png',
        3: 'icon_allPerfect.png',
    }
    pics = []

    # 总高度 查看所有歌曲时高度适当增加
    finalHeight = 1750 if oneRowCount is None else 2800

    # 每行显示的歌曲数
    if oneRowCount is None:
        oneRowCount = 0
        for rank in musicData:
            if len(musicData[rank]) > oneRowCount:
                oneRowCount = len(musicData[rank])

    # 每一个难度分开画
    for rank in musicData:
        rows = int((len(musicData[rank]) - 1) / oneRowCount) + 1
        singleRank = Image.new("RGBA", (oneRowCount * 130 + 100, rows * 130 + 105), (0, 0, 0, 0))
        draw = ImageDraw.Draw(singleRank)
        font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Bold.otf'), 45)

        shadow = Image.new("RGBA", (oneRowCount * 130 + 45, rows * 130 + 77), (0, 0, 0, 0))
        shadow.paste(Image.new("RGBA", (oneRowCount * 130 + 35, rows * 130 + 67), (0, 0, 0, 170)), (5, 5))
        shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        r, g, b, mask = shadow.split()
        singleRank.paste(shadow, (45, 30), mask)

        draw.rectangle((45, 28, oneRowCount * 130 + 75, rows * 130 + 90), fill=(255, 255, 255))

        draw.ellipse((22, 0, 80, 58), fill=color[difficulty])
        draw.rectangle((51, 0, 134, 58), fill=color[difficulty])
        draw.ellipse((105, 0, 163, 58), fill=color[difficulty])
        draw.text((45, -7), rank, (255, 255, 255), font)
        row = 0
        i = 0
        for musicId in musicData[rank]:
            jacket = await pjsk_update_manager.get_asset(
                'startapp/thumbnail/music_jacket', f'jacket_s_{str(musicId).zfill(3)}.png'
            )
            jacket = jacket.resize((120, 120))
            singleRank.paste(jacket, (70 + 130 * i, 72 + 130 * row))
            if musicResult is not None:
                icon = Image.open(data_path / f'pics/{iconName[musicResult[musicId][diff[difficulty]]]}')
                r, g, b, mask = icon.split()
                singleRank.paste(icon, (162 + 130 * i, 164 + 130 * row), mask)
            i += 1
            if i == oneRowCount:
                i = 0
                row += 1
        pics.append(singleRank)

    # 将所有难度合并
    height = 0
    for singlePic in pics:
        height += singlePic.size[1]
    colunm = int(height / finalHeight) + 1
    pic = Image.new("RGBA", ((oneRowCount * 130 + 100) * colunm, height if colunm == 1 else finalHeight), (0, 0, 0, 0))
    pos = [0, 0]
    for singlePic in pics:
        if pos[1] + singlePic.size[1] > finalHeight:
            pos[0] += oneRowCount * 130 + 100
            pos[1] = 0
        r, g, b, mask = singlePic.split()
        pic.paste(singlePic, (pos[0], pos[1]), mask)
        pos[1] += singlePic.size[1] - 20

    # 由于末尾空出的空间相加可能会导致行数+1 这里裁剪一下
    pic = pic.crop((0, 0, pos[0] + oneRowCount * 130 + 160, pic.size[1]))
    return pic