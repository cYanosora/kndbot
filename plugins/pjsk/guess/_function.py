import json
import random
import jieba.posseg as pseg
from .._config import data_path


def getSongLevel(musicid: int, diff: str = 'master') -> str:
    """
    根据musicId获取歌曲对应难度的定数
    """
    with open(data_path / 'musicDifficulties.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    target = filter(lambda x:x['musicId'] == musicid and x['musicDifficulty'] == diff, data)
    try:
        music = next(target)
        level = music['playLevel']
        level = '33+' if level >= 33 else str(level)
    except StopIteration:
        return ''
    return f'此曲的难度是{level}'


def getSongSinger(musicid: int) -> str:
    with open(data_path / 'musicVocals.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    target = filter(lambda x: x['musicId'] == musicid, data)
    ver = ''
    charainfos = []
    for vocal in target:
        if vocal['musicVocalType'] == "sekai":
            ver = 'SEKAI版'
            charainfos = vocal['characters']
            break
        elif vocal['musicVocalType'] == "instrumental":
            ver = '纯音乐版'
            charainfos = vocal['characters']
            break
        elif vocal['musicVocalType'] == "virtual_singer":
            ver = 'V版'
            charainfos = vocal['characters']
        elif vocal['musicVocalType'] == "original_song":
            ver = '原曲版'
            charainfos = vocal['characters']
        elif not ver and vocal['musicVocalType'] == "april_fool_2022":
            ver = '2022愚人节版'
            charainfos = vocal['characters']
        elif not ver and vocal['musicVocalType'] == "another_vocal":
            ver = 'anvo版'
            charainfos = vocal['characters']
        else:
            ver = vocal['musicVocalType']
            charainfos = vocal['characters']
    if not charainfos:
        reply = f'此歌曲只有{ver}'
    else:
        charainfo = random.choice(charainfos)
        charaname = '-'
        if charainfo['characterType'] == 'game_character':
            with open(data_path / 'gameCharacters.json', 'r', encoding='utf-8') as f:
                gameCharacters = json.load(f)
            for gamechara in gameCharacters:
                if gamechara['id'] == charainfo['characterId']:
                    charaname = gamechara.get('firstName', '') + gamechara.get('givenName', '')
        elif charainfo['characterType'] == 'game_character':
            charaname = {
                1: "GUMI", 2: "IA", 3: "flower",
                4: "VY2V3", 5: "音街ウナ", 6: "歌爱ユキ",
                7: "ネネロボ", 8: "ミクダヨー", 9: "可不",
                10: "神威がくぽ", 11: "星界", 12: "東北きりたん",
                13: "ゲキヤク"
            }.get(charainfo['characterId'], '-')
        if len(charainfos) == 1:
            reply = f'{charaname}是此曲{ver}的歌手'
        else:
            reply = f'{charaname}是此曲{ver}的歌手之一'
    return reply


def getSongAuthor(musicid: int) -> str:
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    authors = {}
    for music in data:
        if music['id'] == musicid:
            authors['作词'] = music['lyricist']
            authors['作曲'] = music['composer']
            authors['编曲'] = music['arranger']
    if len(set(authors.values())) == 1:
        author = authors['作曲']
        return f'此曲的作者是{author}'
    else:
        key = random.choice(['作词','作曲','编曲'])
        return f'此曲的{key}是{authors[key]}'


def getCharaUnit(charaid: int) -> str:
    with open(data_path / 'gameCharacterUnits.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    unit = ''
    for charaUnit in data:
        if charaUnit['id'] == charaid:
            unit = charaUnit['unit']
            break
    unitname = {
        'piapro': 'VS', 'school_refusal':'25h',
        'theme_park':'ws','street':'vbs',
        'idol': 'mmj', 'light_sound': 'ln'
    }.get(unit, '')
    return f'此角色来自{unitname}组合'


def getCharaInfo(charaid: int) -> str:
    with open(data_path / 'characterProfiles.json', 'r', encoding='utf-8') as f:
        characterProfiles = json.load(f)
    profile = characterProfiles[str(charaid)]
    height = profile['height'].replace('cm', '')
    school = profile.get('school')
    gender = {
        '11': 'male', '12':'male','13':'male','16':'male','20':'secret','23':'male','26':'male'
    }.get(str(charaid), 'female')
    info = []
    if school and school != '通信制高中':
        info.append(f'此角色来自{school}')
    if gender != 'secret':
        sex = '男性' if gender == 'male' else '女性'
        info.append(f'此角色是{sex}')
    if height.isdigit():
        mean = (int(height)-1)//10*10+5
        info.append(f'此角色的身高为{mean-5}~{mean+5}cm')
    return random.choice(info)


def getCharaBirth(charaid: int) -> str:
    with open(data_path / 'characterProfiles.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    profile = data[str(charaid)]
    birth_month = profile['birthday'].split('月')[0]
    return f'此角色的生日在{birth_month}月'


def getCharaFeature(charaid: int) -> str:
    with open(data_path / 'characterProfiles.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    profile = data[str(charaid)]
    feature_lst = ['hobby', 'specialSkill', 'weak', 'favoriteFood', 'hatedFood']
    key = feature_lst.pop(random.randint(0, len(feature_lst)-1))
    result = ''
    cnt = 0
    while not result:
        cnt += 1
        cuts = list(pseg.cut(profile[key]))
        res = ''
        for pair in cuts:
            if pair.flag in ['an', 'n', 'nr', 'nr1', 'nr2', 'nrj', 'nrf', 'ns', 'nsf', 'nt', 'nz', 'nl', 'ng']:
                res += pair.word
            else:
                res += ' '
        res = res.split()
        feature = {
            'hobby': '爱好', 'specialSkill': '特技', 'weak': '弱点',
            'favoriteFood': '喜欢的食物', 'hatedFood': '讨厌的食物'
        }.get(key)
        if not res:
            if cnt >= 3:
                result = f'此角色的{feature}是{profile[key]}'
                break
            key = feature_lst.pop(random.randint(0, len(feature_lst) - 1))
            continue
        word = random.choice(res)
        if word == profile[key]:
            result = f'此角色的{feature}是{word}'
        else:
            result = f'此角色的{feature}与{word}有关'
    return result
