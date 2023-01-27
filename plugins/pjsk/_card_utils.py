from PIL import Image, ImageDraw, ImageFont
from configs.path_config import FONT_PATH
from ._autoask import pjsk_update_manager
from ._config import data_path
try:
    import ujson as json
except:
    import json
import os


# 获取卡面类型
def cardtype(cardid, cardCostume3ds, costume3ds):
    # 普通0 限定1
    costume = []
    for i in cardCostume3ds:
        if i['cardId'] == cardid:
            costume.append(i['costume3dId'])
    for costumeid in costume:
        for model in costume3ds:
            if model['id'] == costumeid:
                if model['partType'] == 'hair':
                    return 1
    return 0


# 生成卡面缩略图
async def cardthumnail(cardid, istrained=False, cards=None, limitedbadge=False):
    if cards is None:
        with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
            cards = json.load(f)
    if istrained:
        suffix = 'after_training'
    else:
        suffix = 'normal'
    for card in cards:
        if card['id'] == cardid:
            if card['cardRarityType'] != 'rarity_3' and card['cardRarityType'] != 'rarity_4':
                suffix = 'normal'
            pic = await pjsk_update_manager.get_asset(
                f'startapp/thumbnail/chara', f'{card["assetbundleName"]}_{suffix}.png'
            )
            pic = pic.resize((156, 156))
            cardFrame = Image.open(data_path / f'chara/cardFrame_{card["cardRarityType"]}.png')
            r, g, b, mask = cardFrame.split()
            pic.paste(cardFrame, (0, 0), mask)
            if card['cardRarityType'] == 'rarity_1':
                star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((28, 28))
                r, g, b, mask = star.split()
                pic.paste(star, (10, 118), mask)
            if card['cardRarityType'] == 'rarity_2':
                star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((28, 28))
                r, g, b, mask = star.split()
                pic.paste(star, (10, 118), mask)
                pic.paste(star, (36, 118), mask)
            if card['cardRarityType'] == 'rarity_3':
                if istrained:
                    star = Image.open(data_path / f'chara/rarity_star_afterTraining.png')
                else:
                    star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((28, 28))
                r, g, b, mask = star.split()
                pic.paste(star, (10, 118), mask)
                pic.paste(star, (36, 118), mask)
                pic.paste(star, (62, 118), mask)
            if card['cardRarityType'] == 'rarity_4':
                if istrained:
                    star = Image.open(data_path / f'chara/rarity_star_afterTraining.png')
                else:
                    star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((28, 28))
                r, g, b, mask = star.split()
                pic.paste(star, (10, 118), mask)
                pic.paste(star, (36, 118), mask)
                pic.paste(star, (62, 118), mask)
                pic.paste(star, (88, 118), mask)
            if card['cardRarityType'] == 'rarity_birthday':
                star = Image.open(data_path / f'chara/rarity_birthday.png')
                star = star.resize((28, 28))
                r, g, b, mask = star.split()
                pic.paste(star, (10, 118), mask)
            attr = Image.open(data_path / f'chara/icon_attribute_{card["attr"]}.png')
            attr = attr.resize((35, 35))
            r, g, b, mask = attr.split()
            pic.paste(attr, (1, 1), mask)
            if limitedbadge:
                badge = Image.open(data_path / f'pics/badge_limited.png')
                r, g, b, mask = badge.split()
                pic.paste(badge, (43, 0), mask)

            return pic


# 获取角色名称
def getcharaname(characterid, gameCharacters=None):
    if gameCharacters is None:
        with open(data_path / 'gameCharacters.json', 'r', encoding='utf-8') as f:
            gameCharacters = json.load(f)
    for i in gameCharacters:
        if i['id'] == characterid:
            try:
                return i['firstName'] + i['givenName']
            except KeyError:
                return i['givenName']


# 生成单张缩略图信息
async def findcardsingle(card, allcards, cardCostume3ds, costume3ds, skills, gameCharacters):
    pic = Image.new("RGB", (420, 260), (255, 255, 255))
    badge = False
    cardtypenum = cardtype(card['id'], cardCostume3ds, costume3ds)
    if cardtypenum == 1 or card['cardRarityType'] == 'rarity_birthday':
        badge = True
    if card['cardRarityType'] == 'rarity_3' or card['cardRarityType'] == 'rarity_4':
        thumnail = await cardthumnail(card['id'], istrained=False, cards=allcards, limitedbadge=badge)
        r, g, b, mask = thumnail.split()
        pic.paste(thumnail, (45, 15), mask)

        thumnail = await cardthumnail(card['id'], istrained=True, cards=allcards, limitedbadge=badge)
        r, g, b, mask = thumnail.split()
        pic.paste(thumnail, (220, 15), mask)
    else:
        thumnail = await cardthumnail(card['id'], istrained=False, cards=allcards, limitedbadge=badge)
        r, g, b, mask = thumnail.split()
        pic.paste(thumnail, (132, 15), mask)

    draw = ImageDraw.Draw(pic)
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 28)
    text_width = font.getsize(card["prefix"])

    if text_width[0] > 420:
        font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), int(28 / (text_width[0] / 420)))
        text_width = font.getsize(card["prefix"])

    text_coordinate = ((210 - text_width[0] / 2), int(195 - text_width[1] / 2))
    draw.text(text_coordinate, card["prefix"], '#000000', font)

    name = getcharaname(card['characterId'], gameCharacters)
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 18)
    text_width = font.getsize(f'id:{card["id"]}  {name}')
    text_coordinate = ((210 - text_width[0] / 2), int(230 - text_width[1] / 2))
    draw.text(text_coordinate, f'id:{card["id"]}  {name}', '#505050', font)

    for skill in skills:
        if skill['id'] == card['skillId']:
            descriptionSpriteName = skill['descriptionSpriteName']
            skillTypePic = Image.open(data_path / f'chara/skill_{descriptionSpriteName}.png')
            skillTypePic = skillTypePic.resize((40, 40))
            r, g, b, mask = skillTypePic.split()
            pic.paste(skillTypePic, (370, 210), mask)
            break
    return pic


# 生成带cardframe的卡面大图
async def cardlarge(cardid, istrained=False, cards=None):
    if cards is None:
        with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
            cards = json.load(f)
    if istrained:
        suffix = 'after_training'
    else:
        suffix = 'normal'
    for card in cards:
        if card['id'] == cardid:
            if card['cardRarityType'] != 'rarity_3' and card['cardRarityType'] != 'rarity_4':
                suffix = 'normal'
            pic = await pjsk_update_manager.get_asset(
                f'startapp/character/member/{card["assetbundleName"]}', f'card_{suffix}.png'
            )
            pic = pic.resize((1024, 576))
            cardFrame = Image.open(data_path / f'chara/cardFrame_L_{card["cardRarityType"]}.png')
            r, g, b, mask = cardFrame.split()
            pic.paste(cardFrame, (0, 0), mask)
            if card['cardRarityType'] == 'rarity_1':
                star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((72, 70))
                r, g, b, mask = star.split()
                pic.paste(star, (16, 490), mask)
            if card['cardRarityType'] == 'rarity_2':
                star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((72, 70))
                r, g, b, mask = star.split()
                pic.paste(star, (16, 428), mask)
                pic.paste(star, (16, 490), mask)
            if card['cardRarityType'] == 'rarity_3':
                if istrained:
                    star = Image.open(data_path / f'chara/rarity_star_afterTraining.png')
                else:
                    star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((72, 70))
                r, g, b, mask = star.split()
                pic.paste(star, (16, 366), mask)
                pic.paste(star, (16, 428), mask)
                pic.paste(star, (16, 490), mask)
            if card['cardRarityType'] == 'rarity_4':
                if istrained:
                    star = Image.open(data_path / f'chara/rarity_star_afterTraining.png')
                else:
                    star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((72, 70))
                r, g, b, mask = star.split()
                pic.paste(star, (16, 304), mask)
                pic.paste(star, (16, 366), mask)
                pic.paste(star, (16, 428), mask)
                pic.paste(star, (16, 490), mask)
            if card['cardRarityType'] == 'rarity_birthday':
                star = Image.open(data_path / f'chara/rarity_birthday.png')
                star = star.resize((72, 70))
                r, g, b, mask = star.split()
                pic.paste(star, (16, 490), mask)
            attr = Image.open(data_path / f'chara/icon_attribute_{card["attr"]}.png')
            attr = attr.resize((88, 88))
            r, g, b, mask = attr.split()
            pic.paste(attr, (924, 12), mask)
            return pic

# 获取卡面大图
async def cardidtopic(cardid: int, allcards=None):
    """ 获取卡面大图

    :param cardid: 卡面id
    :param allcards: card.json，可以不传
    """
    if allcards is None:
        with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
            allcards = json.load(f)
    assetbundleName = ''
    cardRarityType = ''
    for card in allcards:
        if card['id'] == cardid:
            assetbundleName = card['assetbundleName']
            cardRarityType = card['cardRarityType']
    if assetbundleName == '':
        return []
    if cardRarityType in ["rarity_3", "rarity_4"]:
        cl = ['card_normal.png', 'card_after_training.png']
    else:
        cl = ['card_normal.png']
    for c in cl:
        await pjsk_update_manager.get_asset(f'startapp/character/member/{assetbundleName}', c)
    path = data_path / f'startapp/character/member/{assetbundleName}'
    files = os.listdir(path)
    files_file = [f for f in files if (path / f).is_file()]
    if not (path / 'card_normal.jpg').exists():  # 频道bot最多发送4MB 这里转jpg缩小大小
        im = Image.open(path / 'card_normal.png')
        im = im.convert('RGB')
        im.save(path / 'card_normal.jpg', quality=95)

    if 'card_after_training.png' in files_file:
        if not (path / 'card_after_training.jpg').exists():  # 频道bot最多发送4MB 这里转jpg缩小大小
            im = Image.open(path / 'card_after_training.png')
            im = im.convert('RGB')
            im.save(path / 'card_after_training.jpg', quality=95)
        return [path / 'card_normal.jpg', path / 'card_after_training.jpg']
    else:
        return [path / 'card_normal.jpg']