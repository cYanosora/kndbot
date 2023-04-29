import datetime
from typing import Optional, Dict, List, Union, Tuple
import pytz
import yaml
from PIL import Image, ImageDraw, ImageFont
from configs.path_config import FONT_PATH
from ._autoask import pjsk_update_manager
from ._card_utils import cardthumnail
from ._common_utils import union
from ._config import data_path

try:
    import ujson as json
except:
    import json


# 解析组合id
def analysisunitid(unitid, gameCharacterUnits=None):
    if gameCharacterUnits is None:
        with open(data_path / 'gameCharacterUnits.json', 'r', encoding='utf-8') as f:
            gameCharacterUnits = json.load(f)
    for units in gameCharacterUnits:
        if units['id'] == unitid:
            if unitid <= 20:
                return unitid, units['unit'], f'chr_ts_90_{unitid}.png'
            elif units['gameCharacterId'] == 21:
                if unitid != 21:
                    return 21, units['unit'], f'chr_ts_90_21_{unitid - 25}.png'
                else:
                    return 21, 'piapro', f'chr_ts_90_21.png'
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
        if (
            card['characterId'] == charaid
            and card['attr'] == attr
            and ((card['supportUnit'] == unit) if card['supportUnit'] != 'none' else True)
            and card['releaseAt'] < endtime
        ):
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
    bonuspics = []                  # 临时保存加成角色卡图
    base_pos = (750, 380)           # 加成图粘贴的基准位置
    max_width = 1980 - base_pos[0]  # 加成图最大宽度
    max_height = 1210 - base_pos[1] # 加成图最大高度
    offest_size = [0, 0]            # 每张角色各自的加成图的偏移位置
    # 获取各角色加成图以及应该粘贴的位置
    for chara in event.bonusechara:
        bonuspic = await _charabonuspic(chara, event.bonuseattr, cards, gameCharacterUnits, event.aggregateAtorin)
        if bonuspic is not None:
            if offest_size[0] + bonuspic.size[0] > max_width:
                offest_size[0] = 0
                offest_size[1] += bonuspic.size[1] + 15
            bonuspics.append((bonuspic, offest_size[0], offest_size[1]))
            offest_size[0] += bonuspic.size[0] + 55
    # 生成合适大小的角色加成图
    final_bonuspic = Image.new("RGBA", (max_width, offest_size[1] + bonuspics[-1][0].size[1]))
    for bonuspic, x, y in bonuspics:
        mask = bonuspic.split()[-1]
        final_bonuspic.paste(bonuspic, (x, y), mask)
    # 角色加成图过大时自动缩放
    if final_bonuspic.size[1] > max_height:
        newsize = (int(final_bonuspic.size[0] / final_bonuspic.size[1] * max_height), max_height)
        final_bonuspic = final_bonuspic.resize(newsize)
    # 在背景上粘贴角色加成图
    mask = final_bonuspic.split()[-1]
    pic.paste(final_bonuspic, base_pos, mask)
    pic = pic.convert('RGB')
    return pic


# 生成活动图鉴
async def draweventall(
    event_type: Optional[str] = None,
    event_attr: Optional[str] = None,
    event_units_name: Optional[List] = None,
    event_charas_id: Optional[List[Union[int, Tuple[int, str]]]] = None,
    isEqualAllUnits: bool = True,
    isContainAllCharasId: bool = True,
    isTeamEvent: Optional[bool] = None,
    events: Optional[Dict] = None,
    *args, **kwargs
):
    """
    生成活动图鉴
    :param event_type: 筛选的活动类型
    :param event_attr: 筛选的活动属性
    :param event_units_name: 筛选的活动组合
    :param event_charas_id: 筛选的活动出卡角色
    :param isEqualAllUnits: 筛选的活动组合是否需要完全等同所有组合名称，针对event_units_name参数
    :param isContainAllCharasId: 筛选的活动出卡是否需要包含所有角色id，针对event_charas_id参数
    :param isTeamEvent: True时只筛选箱活、False时只筛选混活，会无视除event_type、event_attr的筛选条件
    :param events: events.json
    """
    if events is None:
        with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
            events = json.load(f)
    with open(data_path / 'eventCards.json', 'r', encoding='utf-8') as f:
        eventCards = json.load(f)
    with open(data_path / 'eventDeckBonuses.json', 'r', encoding='utf-8') as f:
        eventDeckBonuses = json.load(f)
    with open(data_path / 'gameCharacterUnits.json', 'r', encoding='utf-8') as f:
        game_character_units = json.load(f)
    with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
        allcards = json.load(f)
    if event_type != 'marathon':
        with open(data_path / 'cheerfulCarnivalTeams.json', 'r', encoding='utf-8') as f:
            allteams = json.load(f)
        with open(data_path / 'translate.yaml', encoding='utf-8') as f:
            trans = yaml.load(f, Loader=yaml.FullLoader)
    font30 = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), size=30)
    font20 = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), size=20)
    font10 = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), size=10)
    # 筛选：指定活动图鉴显示的活动类型
    if event_type is not None:
        events = filter(lambda x: x['eventType'] == event_type, events)
    limit_count = 10  # 单列活动缩略图的个数
    event_size = (835, 230)  # 每张活动图的尺寸
    event_interval = 20  # 每张活动图的行间距
    event_pad = (40, 20, 25, 25)  # 每张活动图的pad
    handbook_interval = 50  # 每列活动概要的列间距
    handbook_pad = (180, 180, 50, 50)  # 整张活动概要的pad
    light_grey = '#dbdbdb'
    dark_grey = '#929292'
    col_event_imgs = []     # 存放每列活动概要
    _tmp_event_imgs = []
    for each in events:
        # ********************************获取活动信息******************************** #
        # 获取活动出卡情况
        event_cards = [i['cardId'] for i in filter(lambda x:x['eventId'] == each['id'], eventCards)]
        # 筛选：指定活动图鉴显示的对应角色/组合
        if event_charas_id:
            _count = 0 if isContainAllCharasId else len(event_charas_id) - 1
            # 获取当期卡的信息
            current_cards = list(filter(lambda x: x['id'] in event_cards, allcards))
            # 遍历所有需要筛选角色
            for each_id in event_charas_id:
                # 若筛选角色在当期卡内
                try:
                    # 针对有附属组合的vocaloid角色
                    if isinstance(each_id, tuple):
                        if next(filter(lambda x: each_id == (x['characterId'],x['supportUnit']), current_cards)):
                            _count += 1
                    # 针对无附属组合的vocaloid角色、sekai角色
                    else:
                        if next(filter(lambda x: each_id == x['characterId'], current_cards)):
                            _count += 1
                # 筛选角色不在当期卡内，next(filter(...))会抛StopIteration异常，pass掉
                except:
                    pass
            if _count < len(event_charas_id):
                continue
        # 获取活动加成角色，属性
        event_bonusecharas = []
        current_bonuse = list(filter(lambda x: x['eventId'] == each['id'], eventDeckBonuses))
        event_bonusecharas.extend(
            bonuse["gameCharacterUnitId"] for bonuse in current_bonuse
            if bonuse['bonusRate'] == 50 and bonuse.get('gameCharacterUnitId')
        )
        event_bonuseattr = next(filter(lambda x: x.get('cardAttr'), current_bonuse))['cardAttr']
        if event_attr is not None and event_bonuseattr != event_attr:
            continue
        tmp_bonuse_charas = []
        for unitid in event_bonusecharas:
            charaid, unit, charapicname = analysisunitid(unitid, game_character_units)
            tmp_bonuse_charas.append({
                'id': charaid,
                'unit': unit,
                'asset': charapicname
            })
        # 对箱活加成角色作额外处理，只对杏二箱(id:37)后箱活作处理，之前的箱活加成角色不用变
        if each['id'] >= 37 and len(set(i['unit'] for i in tmp_bonuse_charas)) == 1:
            for bonuse_chara in tmp_bonuse_charas.copy():
                if bonuse_chara['id'] > 20:
                    tmp_bonuse_charas.remove(bonuse_chara)
            tmp_bonuse_charas.append({
                'unit': tmp_bonuse_charas[0]['unit'],
                'asset': 'vs_90.png'
            })
        event_bonusecharas = tmp_bonuse_charas
        # 加成角色的所属团体
        belong_units = set(map(lambda x: x['unit'], event_bonusecharas))
        if isTeamEvent is True and len(belong_units) != 1:
            continue
        if isTeamEvent is False and len(belong_units) == 1:
            continue
        if event_units_name:
            # 当期加成只能是筛选团体（筛选团体单数时即为筛选箱活）
            if isEqualAllUnits and belong_units != set(event_units_name):
                continue
            # 筛选团体存在当期加成即可（但排除箱活），可以是复数
            if not isEqualAllUnits and not (
                len(set(belong_units)) > 1 and
                set(event_units_name).issubset(belong_units)
            ):
                continue
        # ********************************生成活动图片******************************** #
        event_img = Image.new('RGB', event_size, 'white')
        draw = ImageDraw.Draw(event_img)
        _interval = 10
        _banner_width = 265
        _left_offset = 70
        _team_size = 70
        _team_pad = 5

        # 生成banner图
        bannerpic = await pjsk_update_manager.get_asset(f'ondemand/event_story/{each["assetbundleName"]}/screen_image', 'banner_event_story.png')
        bannerpic = bannerpic.resize((_banner_width, int(_banner_width / bannerpic.width * bannerpic.height)))
        event_img.paste(bannerpic, (_left_offset, 0), bannerpic)

        # 生成活动属性和加成角色图
        bonusechara_pic = []
        for bonusechara in event_bonusecharas:
            unitcolor = {
                'piapro': '#000000',
                'light_sound': '#4455dd',
                'idol': '#88dd44',
                'street': '#ee1166',
                'theme_park': '#ff9900',
                'school_refusal': '#884499',
            }
            # 活动角色边框显示组合色
            _chr_pic = Image.open(data_path / f'chara/{bonusechara["asset"]}').resize((110, 110))
            _bk = Image.new('RGBA', (130, 130))
            ImageDraw.Draw(_bk).ellipse((0, 0, _bk.size[0], _bk.size[1]), unitcolor[bonusechara['unit']])
            _bk.paste(_chr_pic, (10, 10), _chr_pic)
            bonusechara_pic.append(_bk.resize((30, 30)).copy())
        charapic = union(bonusechara_pic, type='col', length=0, interval=2)
        attrpic = Image.open(data_path / f'chara/icon_attribute_{event_bonuseattr}.png').resize((30, 30))
        event_img.paste(attrpic, (bannerpic.width + _left_offset + _interval, 80), attrpic)
        event_img.paste(charapic, (bannerpic.width + _left_offset + _interval + 60, 80), charapic)

        # 如果活动类型为5v5，粘贴team图
        if each['eventType'] == 'cheerful_carnival':
            teams_info = filter(lambda x:x['eventId'] == each['id'], allteams)
            for _i, team_info in enumerate(teams_info):
                team_img = await pjsk_update_manager.get_asset(
                    f'ondemand/event/{each["assetbundleName"]}/team_image', f'{team_info["assetbundleName"]}.png', block=True
                )
                team_img = team_img.resize((_team_size, _team_size))
                team_bk_img = Image.new('RGBA', (_team_size+_team_pad*2, _team_size+_team_pad*2))
                _color = "#00bbdd" if _i%2 else "#ff8833"
                _draw = ImageDraw.Draw(team_bk_img)
                _draw.rounded_rectangle((0,0,_team_size+_team_pad,_team_size+_team_pad), 10, _color, light_grey, 3)
                team_bk_img.paste(team_img,(_team_pad-2, _team_pad-2),team_img)
                try:
                    team_name = trans['cheerful_carnival_teams'][team_info['id']]
                except KeyError:
                    team_name = team_info['teamName']
                pos = (_left_offset+_banner_width+_interval*2+256+_i*(_team_size+2*_team_pad+_interval*3), 0)
                event_img.paste(team_bk_img, (pos[0]+_interval, pos[1]),team_bk_img)
                if _i != 0:
                    draw.text((pos[0]-_interval*2, pos[1]+_team_size//2-15), 'VS', 'black', font20)
                _name_width = font20.getsize(team_name)[0]
                if _name_width > _team_size+2*_interval:
                    _name_width = font10.getsize(team_name)[0]
                    draw.text((pos[0]+(_team_size+2*(_interval+_team_pad)-_name_width)//2, pos[1]+_team_size+_interval), team_name, 'black', font10)
                else:
                    draw.text((pos[0]+(_team_size+2*(_interval+_team_pad)-_name_width)//2, pos[1]+_team_size), team_name, 'black', font20)

        # 生成活动出卡图
        for index, cardid in enumerate(event_cards):
            _c = (await cardthumnail(cardid, False, allcards)).resize((90, 90))
            event_img.paste(_c, (_left_offset + index * 100, bannerpic.height + _interval), _c)
            draw.text((_left_offset + index * (90 + _interval), bannerpic.height + 90 + _interval), f'ID:{cardid}', dark_grey, font10)
        # 生成活动类型和活动时间图
        eventtype = {"marathon": "马拉松(累积点数)", "cheerful_carnival": "欢乐嘉年华(5v5)"}.get(each['eventType'], "")
        startAt = datetime.datetime.fromtimestamp(
            each['startAt'] / 1000, pytz.timezone('Asia/Shanghai')
        ).strftime('%Y/%m/%d %H:%M:%S')
        aggregateAt = datetime.datetime.fromtimestamp(
            each['aggregateAt'] / 1000 + 1, pytz.timezone('Asia/Shanghai')
        ).strftime('%Y/%m/%d %H:%M:%S')
        draw.text((2*_interval, 0), '{:3}'.format(each['id']), 'black', font20)
        draw.text((bannerpic.width + _left_offset + _interval, 0), eventtype, 'black', font20)
        draw.text((bannerpic.width + _left_offset + _interval, 25), f"开始于 {startAt}", 'black', font20)
        draw.text((bannerpic.width + _left_offset + _interval, 50), f"结束于 {aggregateAt}", 'black', font20)

        _tmp_event_imgs.append(event_img.copy())
        # 活动图数量达到每列限制数量
        if len(_tmp_event_imgs) >= limit_count:
            col_event_imgs.append(union(
                _tmp_event_imgs, type='row', bk_color='white',
                interval=event_interval, interval_color=light_grey, interval_size=3,
                padding=event_pad,
                border_type='circle', border_size=4, border_color=dark_grey, border_radius=25
            ))
            _tmp_event_imgs.clear()
    # 拼接未满每列限制数量的剩余活动图
    if len(_tmp_event_imgs) > 0:
        col_event_imgs.append(union(
            _tmp_event_imgs, type='row', bk_color='white',
            interval=event_interval, interval_color=light_grey, interval_size=3,
            padding=event_pad,
            border_type='circle', border_size=4, border_color=dark_grey, border_radius=25
        ))

    # 若没有任何活动满足需求
    if len(col_event_imgs) == 0:
        return None

    # 合成最终的活动图鉴
    _union_img = union(
        col_event_imgs, type='col', padding=handbook_pad, interval=handbook_interval, align_type='top'
    )
    handbook_img = Image.open(data_path / 'pics/cardinfo.png').resize(_union_img.size)
    handbook_img.paste(_union_img, mask=_union_img)

    # 活动图鉴其他标识
    badge_img = Image.open(data_path / 'pics/findevent_badge.png')
    badge_img = badge_img.resize((event_size[0] // 2, int(badge_img.height / badge_img.width * event_size[0] // 2)))
    handbook_img.paste(badge_img, (handbook_pad[2], int(handbook_pad[1] / 3 * 2 - badge_img.height)), badge_img.split()[-1])
    # water_mark = 'Code by Yozora (Github @cYanosora)\nGenerated by Unibot'
    tips = '查活动 + [活动ID] 查询活动详情\n查卡 + [卡面ID] 查询卡面详情'
    draw = ImageDraw.Draw(handbook_img)
    # draw.text(
    #     (handbook_img.width - 500 - handbook_pad[3], handbook_img.height - 50 - handbook_pad[1] // 3),
    #     water_mark,
    #     '#00CCBB',
    #     font30
    # )
    draw.text(
        (handbook_pad[3], handbook_img.height - 50 - handbook_pad[1] // 3),
        tips,
        '#00CCBB',
        font30
    )
    return handbook_img
