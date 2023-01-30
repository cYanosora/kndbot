import time
import random
from PIL import Image
from typing import List, Union
from nonebot.adapters.onebot.v11 import Message
from utils.imageutils import pic2b64
from utils.message_builder import image
from .._config import data_path
from .._autoask import pjsk_update_manager
from .._card_utils import getcharaname
try:
    import ujson as json
except:
    import json


def getcurrentgacha():
    """
    获取当前的gacha卡池信息
    """
    gachas = []
    with open(data_path / 'gachas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    for gacha in data:
        startAt = int(gacha['startAt'])
        endAt = int(gacha['endAt'])
        now = int(round(time.time() * 1000))
        if startAt < now < endAt:
            for gachaBehaviors in gacha['gachaBehaviors']:
                if (
                    gachaBehaviors['costResourceType'] == 'jewel'
                    and gachaBehaviors['gachaBehaviorType'] == 'over_rarity_3_once'
                    and gachaBehaviors['costResourceQuantity'] == 3000
                 ) and (
                    len(gacha['gachaPickups']) > 2 and gacha['name'][:4] != '[復刻]'
                ):
                    gachas.append({
                        'id': str(gacha['id']), 'gachaBehaviorsid': str(gachaBehaviors['id']),
                        'name': gacha['name']
                    })
    return gachas[-1]


async def fakegacha(gachaid: int, num: int, reverse=False) -> Union[str, Message]:
    """
    进行假抽卡
    :param gachaid: 卡池id
    :param num: 抽卡数量
    :param reverse: 四星、二星概率交换
    """
    with open(data_path / 'gachas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    gacha = None
    birthday = False
    for i in range(0, len(data)):
        if data[i]['id'] == gachaid:
            gacha = data[i]
    if gacha is None:
        return f'找不到编号为{gachaid}的卡池，命令:/sekai抽卡 /sekaiXX连 /sekai反抽卡，三个命令后面都可以加卡池id'
    rate4 = 0
    rate3 = 0
    for i in range(0, len(gacha['gachaCardRarityRates'])):
        if gacha['gachaCardRarityRates'][i]['cardRarityType'] == 'rarity_4':
            rate4 = gacha['gachaCardRarityRates'][i]['rate']
            break
        if gacha['gachaCardRarityRates'][i]['cardRarityType'] == 'rarity_birthday':
            rate4 = gacha['gachaCardRarityRates'][i]['rate']
            birthday = True
            break
    for i in range(0, len(gacha['gachaCardRarityRates'])):
        if gacha['gachaCardRarityRates'][i]['cardRarityType'] == 'rarity_3':
            rate3 = gacha['gachaCardRarityRates'][i]['rate']
    if reverse:
        rate4 = 100 - rate4 - rate3
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    reality2 = []
    reality3 = []
    reality4 = []
    allweight = 0
    for detail in gacha['gachaDetails']:
        for card in filter(lambda x: True if x['id'] == detail['cardId'] else False, cards):
            if card['cardRarityType'] == 'rarity_2':
                reality2.append({'id': card['id'], 'prefix': card['prefix'], 'charaid': card['characterId']})
            elif card['cardRarityType'] == 'rarity_3':
                reality3.append({'id': card['id'], 'prefix': card['prefix'], 'charaid': card['characterId']})
            else:
                allweight = allweight + detail['weight']
                reality4.append({'id': card['id'], 'prefix': card['prefix'], 'charaid': card['characterId'],
                                 'weight': detail['weight']})
    alltext = ''
    keytext = ''
    baodi = True
    count4 = 0
    count3 = 0
    count2 = 0
    result = []
    for i in range(1, num + 1):
        if i % 10 == 0 and baodi and reverse is not True:
            baodi = False
            rannum = random.randint(0, int(rate4 + rate3) * 2) / 2
        else:
            rannum = random.randint(0, 100)
        if rannum < rate4:  # 四星
            count4 += 1
            baodi = False
            nowweight = 0
            rannum2 = random.randint(0, allweight - 1)
            for j in range(0, len(reality4)):
                nowweight = nowweight + reality4[j]['weight']
                if nowweight >= rannum2:
                    if birthday:
                        alltext = alltext + "🎀"
                        keytext = keytext + "🎀"
                    else:
                        alltext = alltext + "★★★★"
                        keytext = keytext + "★★★★"
                    if reality4[j]['weight'] == 400000:
                        alltext = alltext + "[当期]"
                        keytext = keytext + "[当期]"
                    alltext = alltext + f"{reality4[j]['prefix']} - {getcharaname(reality4[j]['charaid'])}\n"
                    keytext = keytext + f"{reality4[j]['prefix']} - {getcharaname(reality4[j]['charaid'])}(第{i}抽)\n"
                    result.append(reality4[j]['id'])
                    break
        elif rannum < rate4 + rate3:  # 三星
            count3 += 1
            rannum2 = random.randint(0, len(reality3) - 1)
            alltext = alltext + f"★★★{reality3[rannum2]['prefix']} - {getcharaname(reality3[rannum2]['charaid'])}\n"
            result.append(reality3[rannum2]['id'])
        else:  # 二星
            count2 += 1
            rannum2 = random.randint(0, len(reality3) - 1)
            alltext = alltext + f"★★{reality2[rannum2]['prefix']} - {getcharaname(reality2[rannum2]['charaid'])}\n"
            result.append(reality2[rannum2]['id'])

    if num == 10:
        pic = await gachapic(result)
        return Message(
            f"id:{gacha['id']} [{gacha['name']}]\n" + image(b64=pic2b64(pic))
        )
    elif num < 10:
        return f"id:{gacha['id']}[{gacha['name']}]\n{alltext}"
    else:
        if birthday:
            return f"id:{gacha['id']}[{gacha['name']}]\n{num}抽模拟抽卡，只显示抽到的四星如下:\n{keytext}\n生日卡：{count4} 三星：{count3} 二星：{count2}"
        else:
            return f"id:{gacha['id']}[{gacha['name']}]\n{num}抽模拟抽卡，只显示抽到的四星如下:\n{keytext}\n四星：{count4} 三星：{count3} 二星：{count2}"

# 生成抽卡图
async def gachapic(charas: List):
    pic = Image.open(data_path / f'pics/gacha.png')
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        cards = json.load(f)
    cover = Image.new('RGB', (1550, 600), (255, 255, 255))
    pic.paste(cover, (314, 500))
    for i in range(0, 5):
        cardpic = await gachacardthumnail(charas[i], False, cards)
        cardpic = cardpic.resize((263, 263))
        r, g, b, mask = cardpic.split()
        pic.paste(cardpic, (336 + 304 * i, 520), mask)
    for i in range(0, 5):
        cardpic = await gachacardthumnail(charas[i+5], False, cards)
        cardpic = cardpic.resize((263, 263))
        r, g, b, mask = cardpic.split()
        pic.paste(cardpic, (336 + 304 * i, 825), mask)
    pic = pic.convert('RGB')
    return pic

# 获取gacha卡面缩略图
async def gachacardthumnail(cardid: int, istrained: bool = False, cards=None) -> 'Image':
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
            pic = Image.new('RGBA', (338, 338), (0, 0, 0, 0))
            cardpic = await pjsk_update_manager.get_asset(
                f'startapp/character/member_cutout/{card["assetbundleName"]}', f'{suffix}.png'
            )
            picmask = Image.open(data_path / 'pics/gachacardmask.png')
            r, g, b, mask = picmask.split()
            pic.paste(cardpic, (0, 0), mask)
            cardFrame = Image.open(data_path / f'chara/cardFrame_{card["cardRarityType"]}.png')
            cardFrame = cardFrame.resize((338, 338))
            r, g, b, mask = cardFrame.split()

            pic.paste(cardFrame, (0, 0), mask)
            if card['cardRarityType'] == 'rarity_1':
                star = Image.open(data_path / 'chara/rarity_star_normal.png')
                star = star.resize((61, 61))
                r, g, b, mask = star.split()
                pic.paste(star, (21, 256), mask)
            if card['cardRarityType'] == 'rarity_2':
                star = Image.open(data_path / 'chara/rarity_star_normal.png')
                star = star.resize((60, 60))
                r, g, b, mask = star.split()
                pic.paste(star, (21, 256), mask)
                pic.paste(star, (78, 256), mask)
            if card['cardRarityType'] == 'rarity_3':
                if istrained:
                    star = Image.open(data_path / 'chara/rarity_star_afterTraining.png')
                else:
                    star = Image.open(data_path / 'chara/rarity_star_normal.png')
                star = star.resize((60, 60))
                r, g, b, mask = star.split()
                pic.paste(star, (21, 256), mask)
                pic.paste(star, (78, 256), mask)
                pic.paste(star, (134, 256), mask)
            if card['cardRarityType'] == 'rarity_4':
                if istrained:
                    star = Image.open(data_path / 'chara/rarity_star_afterTraining.png')
                else:
                    star = Image.open(data_path / f'chara/rarity_star_normal.png')
                star = star.resize((60, 60))
                r, g, b, mask = star.split()
                pic.paste(star, (21, 256), mask)
                pic.paste(star, (78, 256), mask)
                pic.paste(star, (134, 256), mask)
                pic.paste(star, (190, 256), mask)
            if card['cardRarityType'] == 'rarity_birthday':
                star = Image.open(data_path / 'chara/rarity_birthday.png')
                star = star.resize((60, 60))
                r, g, b, mask = star.split()
                pic.paste(star, (21, 256), mask)
            attr = Image.open(data_path / f'chara/icon_attribute_{card["attr"]}.png')
            attr = attr.resize((76, 76))
            r, g, b, mask = attr.split()
            pic.paste(attr, (1, 1), mask)
            return pic
