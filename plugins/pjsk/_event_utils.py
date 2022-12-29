from PIL import Image, ImageDraw, ImageFont
from configs.path_config import FONT_PATH
from ._autoask import pjsk_update_manager
from ._card_utils import cardthumnail
from ._config import data_path

try:
    import ujson as json
except:
    import json


# 解析组合id
def analysisunitid(unitid, gameCharacterUnits):
    if unitid <= 20:
        return unitid, "none", f'chr_ts_90_{unitid}.png'
    for units in gameCharacterUnits:
        if units['id'] == unitid:
            if units['gameCharacterId'] == 21:
                if unitid != 21:
                    return 21, units['unit'], f'chr_ts_90_21_{unitid - 25}.png'
                else:
                    return 21, 'none', f'chr_ts_90_21.png'
            else:
                return units['gameCharacterId'], units['unit'], f'chr_ts_90_{units["gameCharacterId"]}_2.png'


# 生成加成角色图
async def _charabonuspic(unitid, attr, cards, gameCharacterUnits, endtime):
    charaid, unit, charapicname = analysisunitid(unitid, gameCharacterUnits)
    img = Image.new('RGBA', (2000, 125), color=(0, 0, 0, 0))

    charapic = Image.open(data_path / f'chara/{charapicname}')
    charapic = charapic.resize((80, 80))
    r, g, b, mask = charapic.split()
    img.paste(charapic, (0, 0), mask)

    attrpic = Image.open(data_path / f'chara/icon_attribute_{attr}.png')
    attrpic = attrpic.resize((80, 80))
    r, g, b, mask = attrpic.split()
    img.paste(attrpic, (84, 0), mask)
    count = 0
    pos = 172
    for card in cards:
        if card['characterId'] == charaid and card['attr'] == attr and card['supportUnit'] == unit and card['releaseAt'] < endtime:
            count += 1
            cardpic = await cardthumnail(card['id'], True, cards)
            cardpic = cardpic.resize((125, 125))
            r, g, b, mask = cardpic.split()
            img.paste(cardpic, (pos, 0), mask)
            pos += 130
    if count == 0:
        return None
    img = img.crop((0, 0, pos, 125))
    return img


# 生成event图片
async def drawevent(event):
    pic = await pjsk_update_manager.get_asset(
        f'ondemand/event_story/{event.assetbundleName}/screen_image', 'story_bg.png'
    )
    chara = await pjsk_update_manager.get_asset(
        f'ondemand/event_story/{event.assetbundleName}/screen_image', 'story_title.png'
    )
    r, g, b, mask = chara.split()
    pic.paste(chara, (-50, 100), mask)
    logo = await pjsk_update_manager.get_asset(
        f'ondemand/event/{event.assetbundleName}/logo', 'logo.png',
        download=False
    )
    if logo is None:
        logo = await pjsk_update_manager.get_asset(
            f'ondemand/event/{event.assetbundleName}/logo/logo', 'logo.png'
        )
    r, g, b, mask = logo.split()
    pic.paste(logo, (50, 800), mask)
    if event.unit != 'none':
        unit = Image.open(data_path / f'pics/logo_{event.unit}.png')
        r, g, b, mask = unit.split()
        pic.paste(unit, (50, 50), mask)
    words = Image.open(data_path / f'pics/event.png')
    r, g, b, mask = words.split()
    pic.paste(words, (0, 0), mask)
    draw = ImageDraw.Draw(pic)
    font_style = ImageFont.truetype(str(FONT_PATH / f"SourceHanSansCN-Medium.otf"), 34)
    draw.text((294, 1090), event.startAt, fill=(255, 255, 255), font=font_style)
    draw.text((294, 1174), event.aggregateAt, fill=(255, 255, 255), font=font_style)
    pos = [763, 138]
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    for card in event.cards:
        cardimg = await cardthumnail(card, True, cards)
        cardimg = cardimg.resize((125, 125))
        r, g, b, mask = cardimg.split()
        pic.paste(cardimg, (pos[0], pos[1]), mask)
        pos[0] += 130
    with open(data_path / 'gameCharacterUnits.json', 'r', encoding='utf-8') as f:
        gameCharacterUnits = json.load(f)
    row = 0
    pos = [750, 380]
    for chara in event.bonusechara:
        bonuspic = await _charabonuspic(chara, event.bonuseattr, cards, gameCharacterUnits, event.aggregateAtorin)
        if bonuspic is not None:
            bonuspic = bonuspic.resize((int(bonuspic.size[0]*0.9), int(bonuspic.size[1]*0.9)))
            if pos[0] + bonuspic.size[0] > 1980:
                pos = [750, 380]
                row += 1
            r, g, b, mask = bonuspic.split()
            pic.paste(bonuspic, (pos[0], pos[1]+140*row), mask)
            pos[0] += bonuspic.size[0] + 50
    pic = pic.convert('RGB')
    return pic


