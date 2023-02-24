import json
import time
from PIL import Image, ImageFont, ImageDraw
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg
from configs.path_config import FONT_PATH
from utils.imageutils import pic2b64
from utils.message_builder import image
from .._autoask import pjsk_update_manager
from .._errors import pjskError
from .._utils import generatehonor, get_userid_preprocess
from .._models import UserProfile
from .._config import data_path, suite_path, BUG_ERROR

__plugin_name__ = "烧烤档案/pjskprofile"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤档案
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询2次
    指令：
        烧烤档案/个人消息/profile/pjskprofile              :查看自己的收歌情况
        烧烤档案/个人消息/profile/pjskprofile @qq          :查看艾特用户的收歌情况(对方必须已绑定烧烤账户)
        烧烤档案/个人消息/profile/pjskprofile 烧烤id        :查看对应烧烤账号的收歌情况
        烧烤档案/个人消息/profile/pjskprofile 活动排名       :查看当期活动排名对应烧烤用户的收歌情况
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["pjskprofile", "烧烤相关", "烧烤档案", "profile", "个人信息"],
}
__plugin_cd_limit__ = {
    "cd": 60, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "user"
}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# pjsk个人档案
pjsk_profile = on_command('烧烤档案', aliases={"profile", "pjskprofile", "个人信息"}, priority=5, block=True)


@pjsk_profile.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    # 参数解析
    state = await get_userid_preprocess(event, msg)
    if reply := state['error']:
        await pjsk_profile.finish(reply, at_sender=True)
    userid = state['userid']
    isprivate = state['private']
    # 获取信息
    profile = UserProfile()
    try:
        await profile.getprofile(userid, 'profile')
    except pjskError as e :
        await pjsk_profile.finish(str(e))
    except:
        await pjsk_profile.finish(BUG_ERROR)
    await pjsk_profile.send("收到", at_sender=True)
    # 生成图片
    id = '保密' if isprivate else userid
    img = Image.open(data_path / 'pics' / 'bg.png')
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    try:
        assetbundleName = ''
        for i in cards:
            if i['id'] == profile.userDecks[0]:
                assetbundleName = i['assetbundleName']
        if profile.special_training[0]:
            cardimg = await pjsk_update_manager.get_asset(
                r'startapp/thumbnail/chara', rf'{assetbundleName}_after_training.png'
            )
        else:
            cardimg = await pjsk_update_manager.get_asset(
                r'startapp/thumbnail/chara', rf'{assetbundleName}_normal.png'
            )
        cardimg = cardimg.resize((151, 151))
        r, g, b, mask = cardimg.split()
        img.paste(cardimg, (118, 51), mask)
    except FileNotFoundError:
        pass
    except AttributeError:
        pass
    draw = ImageDraw.Draw(img)
    font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 45)
    draw.text((295, 45), profile.name, fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype(str(FONT_PATH / "FOT-RodinNTLGPro-DB.ttf"), 20)
    draw.text((298, 116), f'id:{id}', fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype(str(FONT_PATH / "FOT-RodinNTLGPro-DB.ttf"), 34)
    draw.text((415, 157), str(profile.rank), fill=(255, 255, 255), font=font_style)
    font_style = ImageFont.truetype(str(FONT_PATH / "FOT-RodinNTLGPro-DB.ttf"), 22)
    draw.text((182, 318), str(profile.twitterId), fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Medium.otf"), 24)
    if len(profile.word) > 17:
        draw.text((132, 388), profile.word[:17], fill=(0, 0, 0), font=font_style)
        draw.text((132, 424), profile.word[17:], fill=(0, 0, 0), font=font_style)
    else:
        draw.text((132, 388), profile.word, fill=(0, 0, 0), font=font_style)
    error_flag = True
    for i in range(0, 5):
        try:
            assetbundleName = ''
            for j in cards:
                if j['id'] == profile.userDecks[i]:
                    assetbundleName = j['assetbundleName']
            if profile.special_training[i]:
                cardimg = await pjsk_update_manager.get_asset(
                    r'startapp/thumbnail/chara', rf'{assetbundleName}_after_training.png'
                )
            else:
                cardimg = await pjsk_update_manager.get_asset(
                    r'startapp/thumbnail/chara', rf'{assetbundleName}_normal.png'
                )
            r, g, b, mask = cardimg.split()
            img.paste(cardimg, (111 + 128 * i, 488), mask)
        except FileNotFoundError:
            pass
        except AttributeError:
            if error_flag:
                await pjsk_profile.send("部分资源加载失败，重新发送中...")
                error_flag = False
    font_style = ImageFont.truetype(str(FONT_PATH / "FOT-RodinNTLGPro-DB.ttf"), 27)
    for i in range(0, 5):
        text_width = font_style.getsize(str(profile.clear[i]))
        text_coordinate = (int(170 + 132 * i - text_width[0] / 2), int(735 - text_width[1] / 2))
        draw.text(text_coordinate, str(profile.clear[i]), fill=(0, 0, 0), font=font_style)

        text_width = font_style.getsize(str(profile.full_combo[i]))
        text_coordinate = (int(170 + 132 * i - text_width[0] / 2), int(735 + 133 - text_width[1] / 2))
        draw.text(text_coordinate, str(profile.full_combo[i]), fill=(0, 0, 0), font=font_style)

        text_width = font_style.getsize(str(profile.full_perfect[i]))
        text_coordinate = (int(170 + 132 * i - text_width[0] / 2), int(735 + 2 * 133 - text_width[1] / 2))
        draw.text(text_coordinate, str(profile.full_perfect[i]), fill=(0, 0, 0), font=font_style)

    character = 0
    font_style = ImageFont.truetype(str(FONT_PATH / "FOT-RodinNTLGPro-DB.ttf"), 29)
    for i in range(0, 5):
        for j in range(0, 4):
            character = character + 1
            characterRank = 0
            for charas in profile.characterRank:
                if charas['characterId'] == character:
                    characterRank = charas['characterRank']
                    break
            text_width = font_style.getsize(str(characterRank))
            text_coordinate = (int(920 + 183 * j - text_width[0] / 2), int(686 + 88 * i - text_width[1] / 2))
            draw.text(text_coordinate, str(characterRank), fill=(0, 0, 0), font=font_style)

    for i in range(0, 2):
        for j in range(0, 4):
            character = character + 1
            characterRank = 0
            for charas in profile.characterRank:
                if charas['characterId'] == character:
                    characterRank = charas['characterRank']
                    break
            text_width = font_style.getsize(str(characterRank))
            text_coordinate = (int(920 + 183 * j - text_width[0] / 2), int(510 + 88 * i - text_width[1] / 2))
            draw.text(text_coordinate, str(characterRank), fill=(0, 0, 0), font=font_style)
            if character == 26:
                break
    # 添加牌子图片
    for i in profile.userProfileHonors:
        try:
            if i['seq'] == 1:
                honorpic = await generatehonor(i, True)
                honorpic = honorpic.resize((266, 56))
                r, g, b, mask = honorpic.split()
                img.paste(honorpic, (104, 228), mask)
            elif i['seq'] == 2:
                honorpic = await generatehonor(i, False)
                honorpic = honorpic.resize((126, 56))
                r, g, b, mask = honorpic.split()
                img.paste(honorpic, (375, 228), mask)
            elif i['seq'] == 3:
                honorpic = await generatehonor(i, False)
                honorpic = honorpic.resize((126, 56))
                r, g, b, mask = honorpic.split()
                img.paste(honorpic, (508, 228), mask)
        except AttributeError:
            if error_flag:
                await pjsk_profile.send("部分资源加载失败，重新发送中...")
                error_flag = False
    # 添加文字
    draw.text((952, 141), f'{profile.mvpCount}回', fill=(0, 0, 0), font=font_style)
    draw.text((1259, 141), f'{profile.superStarCount}回', fill=(0, 0, 0), font=font_style)
    try:
        chara = Image.open(data_path / 'chara' / f'chr_ts_{profile.characterId}.png')
        chara = chara.resize((70, 70))
        r, g, b, mask = chara.split()
        img.paste(chara, (952, 293), mask)
        draw.text((1032, 315), str(profile.highScore), fill=(0, 0, 0), font=font_style)
    except:
        pass
    if not profile.isNewData:
        font_style = ImageFont.truetype(str(FONT_PATH / "SourceHanSansCN-Bold.otf"), 25)
        mtime = (suite_path / f'{userid}.json').stat().st_mtime
        updatetime = time.localtime(mtime)
        draw.text(
            (68, 10), '数据上传时间：' + time.strftime("%Y-%m-%d %H:%M:%S", updatetime),
            fill=(100, 100, 100), font=font_style
        )
    # 发送图片
    await pjsk_profile.finish(image(b64=pic2b64(img)))
