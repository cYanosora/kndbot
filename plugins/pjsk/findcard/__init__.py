import os
from PIL import Image
from nonebot import on_command, require
from nonebot.adapters.onebot.v11 import GROUP, Message, GroupMessageEvent
from nonebot.params import CommandArg
from .._config import data_path
from .._card_utils import cardidtopic, findcardsingle
from utils.message_builder import image
from .._models import CardInfo

try:
    require('image_management')
    require('pjsk_images')
    from plugins.image_management.pjsk_images.pjsk_db_source import PjskAlias
    search_flag = True
except:
    search_flag = False
    pass
try:
    import ujson as json
except:
    import json
__plugin_name__ = "卡面查询/findcard"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤卡面信息，移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    限制每个群半分钟只能查询2次
    指令：
        findcard [角色名]                                : 查看角色名对应卡面概览
        findcard [角色名] [一星/1/二星/2/三星/3/生日/四星/4] : 查看角色名对应类型的卡面概览
        查卡/cardinfo [卡面id]                           : 查看卡面详细信息
        card     [卡面id]                               : 查看卡面id对应的特训前后卡面大图
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["findcard", "烧烤相关", "uni移植",  "卡面查询"],
}
__plugin_cd_limit__ = {"cd": 30, "count_limit": 2, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# findcard
findcard = on_command('findcard', aliases={"查卡", "查询卡面"}, permission=GROUP, priority=5, block=True)
card = on_command('card', permission=GROUP, priority=5, block=True)
cardinfo = on_command('cardinfo', permission=GROUP, priority=4, block=True)


async def alias2id(alias: str, group_id: int):
    dic = {
        'ick': 1, 'saki': 2, 'hnm': 3, 'shiho': 4,
        'mnr': 5, 'hrk': 6, 'airi': 7, 'szk': 8,
        'khn': 9, 'an': 10, 'akt': 11, 'toya': 12,
        'tks': 13, 'emu':14, 'nene': 15, 'rui': 16,
        'knd': 17, 'mfy': 18, 'ena': 19, 'mzk': 20,
        'miku': 21, 'rin': 22, 'len': 23, 'luka': 24, 'meiko': 25, 'kaito': 26
    }
    _id = dic.get(alias, 0)
    if _id == 0 and search_flag:
        name = await PjskAlias.query_name(alias, group_id=group_id)
        return dic.get(name, 0)
    else:
        return _id


@findcard.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    alias = arg.extract_plain_text().strip()
    if alias.isdigit():
        await _cardinfo(arg)
        return
    dic = {
        '一星': 'rarity_1',
        '1':'rarity_1',
        '二星': 'rarity_2',
        '2':'rarity_2',
        '三星': 'rarity_3',
        '3':'rarity_3',
        '四星': 'rarity_4',
        '4':'rarity_4',
        '生日': 'rarity_birthday',
    }
    for _type in dic.keys():
        if alias.endswith(_type):
            alias = alias[:-len(_type)].strip()
            cardRarityType = dic[_type]
            break
    else:
        cardRarityType = None
    charaid = await alias2id(alias, event.group_id)
    if charaid == 0:
        await findcard.finish('找不到你说的角色哦')
    # 识别到角色，发送卡图
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        allcards = json.load(f)
    with open(data_path / 'cardCostume3ds.json', 'r', encoding='utf-8') as f:
        cardCostume3ds = json.load(f)
    with open(data_path / 'costume3ds.json', 'r', encoding='utf-8') as f:
        costume3ds = json.load(f)
    allcards.sort(key=lambda x: x["releaseAt"], reverse=True)
    # 获得卡面的数量，决定是否更新缓存
    count = 0
    for card in allcards:
        if card['characterId'] == charaid:
            if cardRarityType is not None:
                if card['cardRarityType'] != cardRarityType:
                    continue
            count += 1
    # 检查本地缓存图片数量是否一致
    path = data_path / f'cardinfo'
    path.mkdir(parents=True, exist_ok=True)
    savepath = path / f'{charaid}_{cardRarityType if cardRarityType is not None else "all"}_{count}.png'
    if savepath.exists():
        await findcard.finish(image(savepath))
    else:
        # 删除过去的卡图
        for i in os.listdir(path):
            if i.startswith(f'{charaid}_{cardRarityType if cardRarityType is not None else "all"}'):
                os.remove(path / i)
        # 生成新卡图
        count = 0
        pic = Image.new('RGB', (1500, 5000), (235, 235, 235))
        error_flag = False
        for card in allcards:
            if card['characterId'] == charaid:
                if cardRarityType is not None:
                    if card['cardRarityType'] != cardRarityType:
                        continue
                try:
                    single = await findcardsingle(card, allcards, cardCostume3ds, costume3ds)
                    pos = (int(70 + count % 3 * 470), int(count / 3) * 310 + 60)
                    count += 1
                    pic.paste(single, pos)
                except AttributeError:
                    error_flag = True
                    continue
        if error_flag:
            await findcard.send("部分资源加载失败，重新发送中...")
        pic = pic.crop((0, 0, 1500, (int((count - 1) / 3) + 1) * 310 + 60))
        pic.save(savepath)
        await findcard.finish(image(savepath))


@card.handle()
async def _card(arg: Message = CommandArg()):
    card_id = arg.extract_plain_text().strip()
    try:
        card_id = int(card_id)
    except:
        return
    pic_paths = await cardidtopic(card_id)
    await card.finish(Message([image(i) for i in pic_paths]))


@cardinfo.handle()
async def _cardinfo(arg: Message = CommandArg()):
    card_id = arg.extract_plain_text().strip()
    try:
        card_id = int(card_id)
    except:
        return
    path = data_path / f'infocard'
    path.mkdir(parents=True, exist_ok=True)
    file = path / f'id_{arg}.jpg'
    if not file.exists():
        card = CardInfo()
        await card.getinfo(card_id)
        pic = await card.toimg()
        pic = pic.convert('RGB')
        pic.save(file, quality=85)
    await cardinfo.finish(image(file))
