import os
from PIL import Image, ImageFont, ImageDraw
from configs.path_config import FONT_PATH
from .._autoask import pjsk_update_manager
from .._config import data_path
from .._data_source import cardthumnail
try:
    import ujson as json
except:
    import json


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


def getcharaname(characterid):
    with open(data_path / 'gameCharacters.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    for i in data:
        if i['id'] == characterid:
            try:
                return i['firstName'] + i['givenName']
            except KeyError:
                return i['givenName']


async def findcardsingle(card, allcards, cardCostume3ds, costume3ds):
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
    text_width = font.getsize(f'{card["id"]}. {card["prefix"]}')
    text_coordinate = ((210 - text_width[0] / 2), int(195 - text_width[1] / 2))
    draw.text(text_coordinate, f'{card["id"]}. {card["prefix"]}', '#000000', font)

    name = getcharaname(card['characterId'])
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 18)
    text_width = font.getsize(name)
    text_coordinate = ((210 - text_width[0] / 2), int(230 - text_width[1] / 2))
    draw.text(text_coordinate, name, '#505050', font)

    return pic


async def cardidtopic(cardid):
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