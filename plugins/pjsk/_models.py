import math
import random
import time
import requests
import yaml
import pytz
import datetime
from typing import List, Dict, Union, Optional
from PIL import Image, ImageDraw, ImageFilter
from services import logger
from services.db_context import db
from ._autoask import pjsk_update_manager
from ._card_utils import cardthumnail, cardlarge
from ._common_utils import t2i, union, callapi
from ._config import api_base_url_list, data_path
from ._event_utils import analysisunitid

try:
    import ujson as json
except:
    import json


class PjskGuessRank(db.Model):
    __tablename__ = "pjsk_guess_rank"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    game_type = db.Column(db.TEXT(), nullable=False)
    total_count = db.Column(db.JSON(), default={}, nullable=False)
    daily_count = db.Column(db.Integer(), default=0, nullable=False)
    last_guess_time = db.Column(db.DateTime(), nullable=False, default=datetime.datetime.min)

    @classmethod
    async def get_rank(cls, group_id: int, game_type: str, guess_diff: Optional[int] = None):
        """
        说明：
            获取某群某类型游戏的用户排行榜
        参数：
            :param group_id: 群号
            :param game_type: 游戏类型
            :param guess_diff: 游戏难度
        """
        user_ls = []
        count_ls = []
        query = cls.query.where((cls.group_id == group_id) & (cls.game_type == game_type))
        if guess_diff is not None:
            for user in await query.gino.all():
                if count := user.total_count.get(str(guess_diff), 0):
                    user_ls.append(user.user_qq)
                    count_ls.append(count)
        else:
            for user in await query.gino.all():
                total = user.total_count
                count = sum(total.get(i) for i in total.keys())
                user_ls.append(user.user_qq)
                count_ls.append(count)
        return user_ls, count_ls

    @classmethod
    async def add_count(
        cls, user_qq: int, group_id: int, game_type: str, guess_diff: int
    ) -> bool:
        """
        说明：
            添加次数
        参数：
            :param user_qq: qq号
            :param group_id: 群号
            :param game_type: 游戏类型
            :param guess_diff: 游戏难度
        """
        user = await cls._get_user_info(user_qq, group_id, game_type)
        guess_diff = str(guess_diff)
        total_count = user.total_count
        total_count[guess_diff] = total_count.get(guess_diff, 0) + 1
        lastdate = user.last_guess_time.date()
        nowdate = datetime.datetime.now().date()
        daily_count = 1 if nowdate > lastdate else user.daily_count+1
        await user.update(
            total_count=total_count,
            daily_count=daily_count,
            last_guess_time=datetime.datetime.now()
        ).apply()
        return False if await cls.check_today_count(user_qq, group_id) else True

    @classmethod
    async def _get_user_info(cls,user_qq: int, group_id: int, game_type: str):
        """
        说明：
            获取用户信息
        参数：
            :param user_qq: qq号
            :param group_id: 群号
            :param game_type: 游戏类型
        """
        user = await cls.query.where(
            (cls.user_qq == user_qq) & (cls.group_id == group_id) & (cls.game_type == game_type)
        ).gino.first()
        return user or await cls.create(
            user_qq=user_qq,
            group_id=group_id,
            game_type=game_type,
            total_count={},
            daily_count=0,
            last_guess_time=datetime.datetime.now().date()
        )

    @classmethod
    async def check_today_count(cls, user_qq: int, group_id: int) -> bool:
        """
        说明：
            检查用户是否达到游戏获取金币上限
        参数：
            :param user_qq: qq号
            :param group_id: 群号
        """
        users = await cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id)).gino.all()
        last_date = max(user.last_guess_time.date() for user in users)
        daily_count = sum(user.daily_count for user in users)
        return True if(
            last_date >= datetime.datetime.now().date() and daily_count >= 10
        ) else False



class PjskSongsAlias(db.Model):
    __tablename__ = "pjsk_songs_alias"
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer(), primary_key=True)
    song_id = db.Column(db.Integer(), nullable=False)
    song_alias = db.Column(db.Unicode(), nullable=False)  # 包括曲名、翻译、玩家起的昵称
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    join_time = db.Column(db.DateTime(), nullable=False)
    is_pass = db.Column(db.Boolean(), default=False)
    _idx1 = db.Index("pjsk_alias_idx1", "song_id", "song_alias", unique=True)

    @classmethod
    async def add_alias(
            cls, song_id: int, alias: str, user_qq: int, group_id: int,
            join_time: datetime.datetime, is_pass: bool
    ) -> bool:
        """
        说明：
            添加别名
        参数：
            :param song_id: 歌曲id
            :param user_qq: qq号
            :param group_id: 群号
            :param alias: 别名
            :param join_time: 添加时间
        """
        if not await cls.check_alias_exists(alias):
            await cls.create(
                song_id=song_id, user_qq=user_qq, group_id=group_id,
                song_alias=alias, is_pass=is_pass, join_time=join_time
            )
            return True
        return False

    @classmethod
    async def delete_alias(cls, alias: str) -> bool:
        """
        说明：
            删除别名
        参数：
            :param alias: 别名
        """
        if await cls.check_alias_exists(alias):
            query = cls.query.where(cls.song_alias == alias).with_for_update()
            query = await query.gino.first()
            await query.delete()
            return True
        return False

    @classmethod
    async def check_alias_exists(cls, alias: str) -> bool:
        """
        说明：
            检测别名是否已存在
        参数：
            :param alias: 别名
        """
        query = await cls.select("song_alias").gino.all()
        query = [res[0] for res in query]
        if alias in query:
            return True
        return False

    @classmethod
    async def check_id_exists(cls, song_id: int) -> bool:
        """
        说明：
            检测歌曲id是否已存在
        参数：
            :param name: 主名
        """
        query = await cls.select("song_id").gino.all()
        query = set(res[0] for res in query)
        if song_id in query:
            return True
        return False

    @classmethod
    async def query_alias(cls, song_id: int) -> List[str]:
        """
        说明：
            查找对应歌曲id的所有别称
        参数：
            :param song_id: 歌曲id
        """
        query = await cls.select("song_alias").where(cls.song_id == song_id).gino.all()
        query = [res.song_alias for res in query]
        return query

    @classmethod
    async def query_sid(cls, song_alias: str) -> int:
        """
        说明：
            查找对应别称的歌曲id
        参数：
            :param song_alias: 别名
        """
        query = await cls.select("song_id").where(cls.song_alias == song_alias).gino.scalar()
        return query


class PjskBind(db.Model):
    __tablename__ = "pjsk_bind"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    pjsk_uid = db.Column(db.BigInteger(), nullable=False)
    pjsk_type = db.Column(db.Integer(), default=0, nullable=False)
    isprivate = db.Column(db.Boolean(), default=False, nullable=False)
    _rela = db.Index("pjsk_rela", "user_qq", "pjsk_type", unique=True)

    @classmethod
    async def set_look(
            cls, user_qq: int, isprivate: bool, pjsk_type: int = 0,
    ):
        """
        说明：
            添加绑定信息
        参数：
            :param user_qq: qq号
            :param isprivate: 是否隐藏信息
            :param pjsk_type: pjsk服务器类型(0:日服，1:台服，2:国际服)
        """
        try:
            user = (
                await cls.query.where((cls.user_qq == user_qq) & (cls.pjsk_type == pjsk_type))
                    .with_for_update()
                    .gino.first()
            )
            if user:
                await user.update(isprivate=isprivate).apply()
                return True
        except Exception as e:
            logger.info(f"User {user_qq} 修改pjsk信息公开设定时发生错误 {type(e)}：{e}")
        return False

    @classmethod
    async def add_bind(
            cls, user_qq: int, pjsk_uid: int, pjsk_type: int = 0, isprivate: bool = False
    ) -> bool:
        """
        说明：
            添加绑定信息
        参数：
            :param user_qq: qq号
            :param pjsk_uid: pjsk用户id号
            :param pjsk_type: pjsk服务器类型(0:日服，1:台服，2:国际服)
        """
        try:
            user = (
                await cls.query.where((cls.user_qq == user_qq) & (cls.pjsk_type == pjsk_type))
                    .with_for_update()
                    .gino.first()
            )
            if user:
                await user.update(pjsk_uid=pjsk_uid).apply()
            else:
                await cls.create(
                    user_qq=user_qq,
                    pjsk_uid=pjsk_uid,
                    pjsk_type=pjsk_type,
                    isprivate=isprivate
                )
            return True
        except Exception as e:
            logger.info(f"User {user_qq} 添加pjsk绑定信息时发生错误 {type(e)}：{e}")
            return False

    @classmethod
    async def del_bind(cls, user_qq: int, pjsk_type: int = 0) -> bool:
        """
        说明：
            删除绑定信息
        参数：
            :param user_qq: qq号
            :param pjsk_type: pjsk服务器类型(0:日服，1:台服，2:国际服)
        """
        if await cls.check_alias_exists(user_qq, pjsk_type):
            query = cls.query.where(
                (cls.user_qq == user_qq) & (cls.pjsk_type == pjsk_type)
            ).with_for_update()
            query = await query.gino.first()
            await query.delete()
            return True
        return False

    @classmethod
    async def check_exists(cls, user_qq: int, pjsk_type: int = 0) -> bool:
        """
        说明：
            检测用户是否已存在绑定信息
        参数：
            :param user_qq: qq号:
            :param pjsk_type: pjsk服务器类型(0:日服，1:台服，2:国际服)
        """
        q = await cls.query.where(
            (cls.user_qq == user_qq) & (cls.pjsk_type == pjsk_type)
        ).with_for_update().gino.first()
        if q:
            return True
        return False

    @classmethod
    async def get_user_bind(cls, user_qq: int, pjsk_type: int = 0):
        """
        说明：
            获取用户的绑定信息
        参数：
            :param user_qq: qq号
            :param pjsk_type: pjsk服务器类型(0:日服，1:台服，2:国际服)
        """
        query = await cls.query.where(
            (cls.user_qq == user_qq) & (cls.pjsk_type == pjsk_type)
        ).gino.first()
        if query:
            return query.pjsk_uid, query.isprivate
        return None, False


class UserProfile(object):
    def __init__(self):
        self.name = ''
        self.rank = 0
        self.userid = ''
        self.twitterId = ''
        self.word = ''
        self.userDecks = [0, 0, 0, 0, 0]
        self.special_training = [False, False, False, False, False]
        self.full_perfect = [0, 0, 0, 0, 0]
        self.full_combo = [0, 0, 0, 0, 0]
        self.clear = [0, 0, 0, 0, 0]
        self.mvpCount = 0
        self.superStarCount = 0
        self.userProfileHonors = {}
        self.characterRank = {}
        self.characterId = 0
        self.highScore = 0
        self.masterscore = {}
        self.expertscore = {}
        self.musicResult = {}
        self.isNewData = False
        for i in range(26, 38):
            self.masterscore[i] = [0, 0, 0, 0]
        for i in range(21, 32):
            self.expertscore[i] = [0, 0, 0, 0]

    async def getprofile(self, userid: str, query_type: str = 'unknown', data: Optional[Dict] = None):
        if data is None:
            data = await callapi(random.choice(api_base_url_list) + f'/user/{userid}/profile', query_type=query_type)

        # 有totalPower字段说明是日服新数据
        try:
            data['totalPower']
            self.isNewData = True
            print('新数据')
        except:
            print('suite数据')
            pass

        # 基本信息
        self.userid = userid
        try:
            self.twitterId = data['userProfile']['twitterId']
        except:
            pass
        try:
            self.word = data['userProfile']['word']
        except:
            pass

        # 挑战最高分
        try:
            if self.isNewData:
                self.characterId = data['userChallengeLiveSoloResult']['characterId']
                self.highScore = data['userChallengeLiveSoloResult']['highScore']
            else:
                for i in data['userChallengeLiveSoloResults']:
                    if i['highScore'] > self.highScore:
                        self.characterId = i['characterId']
                        self.highScore = i['highScore']
        except:
            pass
        self.characterRank = data['userCharacters']
        self.userProfileHonors = data['userProfileHonors']

        # 打歌数据
        if self.isNewData:
            self.name = data['user']['name']
            self.rank = data['user']['rank']
            count_data = data['userMusicDifficultyClearCount']
            self.full_perfect = ['无数据' for i in range(5)]
            self.full_combo = [count_data[i]['fullCombo'] for i in range(5)]
            self.clear = [count_data[i]['liveClear'] for i in range(5)]
            self.mvpCount = data['userMultiLiveTopScoreCount']['mvp']
            self.superStarCount = data['userMultiLiveTopScoreCount']['superStar']
        else:
            self.name = data['user']['userGamedata']['name']
            self.rank = data['user']['userGamedata']['rank']
            with open(data_path / f'musics.json', 'r', encoding='utf-8') as f:
                allmusic = json.load(f)
            with open(data_path / f'musicDifficulties.json', 'r', encoding='utf-8') as f:
                musicDifficulties = json.load(f)
            result = {}
            now = int(time.time() * 1000)
            self.masterscore['33+musicId'] = []
            for music in allmusic:
                result[music['id']] = [0, 0, 0, 0, 0]
                if music['publishedAt'] < now:
                    found = [0, 0]
                    for diff in musicDifficulties:
                        if music['id'] == diff['musicId'] and diff['musicDifficulty'] == 'expert':
                            playLevel = diff['playLevel']
                            self.expertscore[playLevel][3] = self.expertscore[playLevel][3] + 1
                            found[0] = 1
                        elif music['id'] == diff['musicId'] and diff['musicDifficulty'] == 'master':
                            playLevel = diff['playLevel']
                            if playLevel >= 34:
                                self.masterscore['33+musicId'].append(music['id'])
                            self.masterscore[playLevel][3] = self.masterscore[playLevel][3] + 1
                            found[1] = 1
                        if found == [1, 1]:
                            break
            for music in data['userMusicResults']:
                musicId = music['musicId']
                musicDifficulty = music['musicDifficulty']
                playResult = music['playResult']
                self.mvpCount = self.mvpCount + music['mvpCount']
                self.superStarCount = self.superStarCount + music['superStarCount']
                if musicDifficulty == 'easy':
                    diffculty = 0
                elif musicDifficulty == 'normal':
                    diffculty = 1
                elif musicDifficulty == 'hard':
                    diffculty = 2
                elif musicDifficulty == 'expert':
                    diffculty = 3
                else:
                    diffculty = 4
                try:
                    if playResult == 'full_perfect':
                        if result[musicId][diffculty] < 3:
                            result[musicId][diffculty] = 3
                    elif playResult == 'full_combo':
                        if result[musicId][diffculty] < 2:
                            result[musicId][diffculty] = 2
                    elif playResult == 'clear':
                        if result[musicId][diffculty] < 1:
                            result[musicId][diffculty] = 1
                except KeyError:
                    pass
            for music in result:
                for i in range(0, 5):
                    if result[music][i] == 3:
                        self.full_perfect[i] = self.full_perfect[i] + 1
                        self.full_combo[i] = self.full_combo[i] + 1
                        self.clear[i] = self.clear[i] + 1
                    elif result[music][i] == 2:
                        self.full_combo[i] = self.full_combo[i] + 1
                        self.clear[i] = self.clear[i] + 1
                    elif result[music][i] == 1:
                        self.clear[i] = self.clear[i] + 1
                    if i == 4:
                        for diff in musicDifficulties:
                            if music == diff['musicId'] and diff['musicDifficulty'] == 'master':
                                playLevel = diff['playLevel']
                                break
                        if result[music][i] == 3:
                            self.masterscore[playLevel][0] += 1
                            self.masterscore[playLevel][1] += 1
                            self.masterscore[playLevel][2] += 1
                        elif result[music][i] == 2:
                            self.masterscore[playLevel][1] += 1
                            self.masterscore[playLevel][2] += 1
                        elif result[music][i] == 1:
                            self.masterscore[playLevel][2] += 1
                    elif i == 3:
                        for diff in musicDifficulties:
                            if music == diff['musicId'] and diff['musicDifficulty'] == 'expert':
                                playLevel = diff['playLevel']
                                break
                        if result[music][i] == 3:
                            self.expertscore[playLevel][0] += 1
                            self.expertscore[playLevel][1] += 1
                            self.expertscore[playLevel][2] += 1
                        elif result[music][i] == 2:
                            self.expertscore[playLevel][1] += 1
                            self.expertscore[playLevel][2] += 1
                        elif result[music][i] == 1:
                            self.expertscore[playLevel][2] += 1
            self.musicResult = result
        for i in range(0, 5):
            # 新数据格式
            if self.isNewData:
                self.userDecks[i] = data['userDeck'][f'member{i + 1}']
            # suite数据格式
            else:
                decknum = data['user']['userGamedata']['deck']
                for deck in data['userDecks']:
                    if deck['deckId'] == decknum:
                        self.userDecks[i] = deck[f'member{i + 1}']
                        break

            for userCards in data['userCards']:
                if userCards['cardId'] != self.userDecks[i]:
                    continue
                if userCards['defaultImage'] == "special_training":
                    self.special_training[i] = True


class MusicInfo(object):

    def __init__(self):
        self.id = 0
        self.title = ''
        self.lyricist = ''
        self.composer = ''
        self.arranger = ''
        self.publishedAt = 0
        self.hot = 0
        self.hotAdjust = 0
        self.length = 0
        self.fullPerfectRate = [0, 0, 0, 0, 0]
        self.fullComboRate = [0, 0, 0, 0, 0]
        self.clearRate = [0, 0, 0, 0, 0]
        self.playLevel = [0, 0, 0, 0, 0]
        self.noteCount = [0, 0, 0, 0, 0]
        self.playLevelAdjust = [0, 0, 0, 0, 0]
        self.fullComboAdjust = [0, 0, 0, 0, 0]
        self.fullPerfectAdjust = [0, 0, 0, 0, 0]
        self.fillerSec = 0


class EventInfo(object):

    def __init__(self):
        self.id = 0
        self.eventType = ''
        self.name = ''
        self.assetbundleName = ''
        self.startAt = ''
        self.aggregateAtorin = 0
        self.aggregateAt = ''
        self.unit = ''
        self.bonusechara = []
        self.bonuseattr = ''
        self.music = 0
        self.cards = []

    def getevent(self, eventid):
        with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        with open(data_path / 'eventCards.json', 'r', encoding='utf-8') as f:
            eventCards = json.load(f)
        with open(data_path / 'eventDeckBonuses.json', 'r', encoding='utf-8') as f:
            eventDeckBonuses = json.load(f)
        for events in data:
            if eventid == events['id']:
                self.id = events['id']
                self.eventType = events['eventType']
                self.name = events['name']
                self.assetbundleName = events['assetbundleName']
                self.startAt = datetime.datetime.fromtimestamp(
                    events['startAt'] / 1000, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')
                self.aggregateAtorin = events['aggregateAt']
                self.aggregateAt = datetime.datetime.fromtimestamp(
                    events['aggregateAt'] / 1000 + 1, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')
                try:
                    self.unit = events['unit']
                except:
                    pass
                break
        if self.id == 0:
            return False
        for cards in eventCards:
            if cards['eventId'] == self.id:
                self.cards.append(cards['cardId'])
        for bonuse in eventDeckBonuses:
            if bonuse['eventId'] == self.id:
                try:
                    self.bonuseattr = bonuse['cardAttr']
                    self.bonusechara.append(bonuse['gameCharacterUnitId'])
                except:
                    pass
        return True


class GachaInfo(object):
    def __init__(self):
        self.id: int = 0
        self.gachaType: str = ''
        self.gachaCardRarityRateGroupId: int = 0
        self.name: str = ''
        self.assetbundleName: str = ''
        self.startAt: str = ''
        self.endAt: str = ''


def cardskill(skillid, skills, description=None):
    for skill in skills:
        if skill['id'] == skillid:
            if description is None:
                description = skill['description']
            count = description.count('{{')
            for i in range(0, count):
                para = description[description.find('{{') + 2:description.find('}}')].split(';')
                for effect in skill['skillEffects']:
                    if effect['id'] == int(para[0]):
                        detail = effect['skillEffectDetails']
                        if para[1] == 'd':
                            replace = '/'.join(str(i["activateEffectDuration"]) for i in detail)
                        elif para[1] == 'e':
                            replace = str(effect['skillEnhance']['activateEffectValue'])
                        elif para[1] == 'm':
                            replace = '/'.join(
                                str(i["activateEffectValue"] + 5*effect['skillEnhance']['activateEffectValue']) for i in detail
                            )
                        else:
                            replace = '/'.join(str(i["activateEffectValue"]) for i in detail)
                        # 全等级效果相同
                        if len(set(replace.split('/'))) == 1:
                            replace = replace.split('/')[0]
                        description = description.replace('{{' + para[0] + ';' + para[1] + '}}', replace, 1)
            return description
    return ''


class CardInfo(object):
    def __init__(self, config: Optional[Dict] = None):
        self.config: Dict[str, bool] = (  # 基础配置
            config if config else {
                'event': True,  # 展示图是否展示出场活动
                'music': True,  # 展示图是否展示活动歌曲
                'gacha': True,  # 展示图是否展示来源卡池
            }
        )

        self.id: int = 0  # 卡面id
        self.characterId: int = 0  # 角色id
        self.costume3dId: int = 0  # 衣装id
        self.skillId: int = 0  # 技能id

        self.unit: str = 'none'  # 所属组合
        self.cardRarityType: str = ''  # 卡面星数
        self.attr: str = ''  # 卡面属性
        self.isLimited: bool = False  # 卡面是否限定
        self.cardParameters: Dict[str, int] = {}  # 卡面综合力
        self.releaseAt: str = ''  # 发布时间

        self.charaName: str = ''  # 角色名称(仅日文)
        self.prefix: str = ''  # 卡面名称(仅日文)
        self.gachaPhrase: Dict[str, str] = {}  # 招募语(含中日文显示)
        self.cardSkillName: Dict[str, str] = {}  # 技能名称(含中日文显示)
        self.cardSkillDes: Dict[str, str] = {}  # 技能效果(含中日文显示)

        self.event: EventInfo = EventInfo()  # 登场活动(如果有的话)
        self.music: MusicInfo = MusicInfo()  # 活动歌曲(如果有的话)
        self.gacha: GachaInfo = GachaInfo()  # 来源卡池(如果有的话)

        # 卡面所需图片资源
        self.assets: Dict[str, Union[str, Dict[str, List[str]]]] = {
            'card': '',  # 卡图
            'costume': {  # 附带衣装
                'hair': [],  # 发型
                'head': [],  # 发饰
                'body': []  # 服装
            },
        }

    def _get_music_info(self):
        if self.event.id == 0:
            # 获取活动id
            with open(data_path / 'eventCards.json', 'r', encoding='utf-8') as f:
                event_cards = json.load(f)
            for each in event_cards:
                if each["cardId"] == self.id:
                    self.event.id = each["eventId"]
                    break
        if self.event.id == 0:
            raise Exception("卡面无对应活动")
        # 获取活动歌曲id
        with open(data_path / 'eventMusics.json', 'r', encoding='utf-8') as f:
            event_musics = json.load(f)
        for each in event_musics:
            if each["eventId"] == self.event.id:
                self.event.music = each["musicId"]
                break
        # 获取活动歌曲信息
        if self.event.music == 0:
            raise Exception("活动无对应歌曲")
        with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
            musics = json.load(f)
        for each_music in musics:
            if each_music["id"] == self.event.music:
                self.music.id = each_music["id"]
                self.music.title = each_music["title"]
                self.music.lyricist = each_music['lyricist']
                self.music.composer = each_music['composer']
                self.music.arranger = each_music['arranger']
                self.music.assetbundleName = each_music["assetbundleName"]
                self.music.publishedAt = each_music['publishedAt']
                break

    def _get_event_info(self):
        """
        根据卡面id获取当期活动信息
        """
        # 获取活动id
        with open(data_path / 'eventCards.json', 'r', encoding='utf-8') as f:
            event_cards = json.load(f)
        for each in event_cards:
            if each["cardId"] == self.id:
                self.event.id = each["eventId"]
                break
        if self.event.id == 0:
            raise Exception('卡面无对应活动')
        # 获取活动信息
        with open(data_path / 'events.json', 'r', encoding='utf-8') as f:
            events = json.load(f)
        for each_event in events:
            if each_event["id"] == self.event.id:
                self.event.eventType = each_event['eventType']
                self.event.name = each_event['name']
                self.event.assetbundleName = each_event['assetbundleName']
                self.event.startAt = datetime.datetime.fromtimestamp(
                    each_event['startAt'] / 1000, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')
                self.event.aggregateAtorin = each_event['aggregateAt']
                self.event.aggregateAt = datetime.datetime.fromtimestamp(
                    each_event['aggregateAt'] / 1000 + 1, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')
                break
        # 获取参与活动的角色信息、活动属性
        with open(data_path / 'eventDeckBonuses.json', 'r', encoding='utf-8') as f:
            eventDeckBonuses = json.load(f)
        for bonuse in eventDeckBonuses:
            if bonuse['eventId'] == self.event.id:
                if not self.event.bonuseattr:
                    try:
                        self.event.bonuseattr = bonuse['cardAttr']
                    except:
                        pass
                try:
                    if bonuse['bonusRate'] == 50:
                        self.event.bonusechara.append(bonuse["gameCharacterUnitId"])
                except:
                    pass

        with open(data_path / 'gameCharacterUnits.json', 'r', encoding='utf-8') as f:
            game_character_units = json.load(f)
        tmp_bonuse_charas = []
        for unitid in self.event.bonusechara:
            charaid, unit, charapicname = analysisunitid(unitid, game_character_units)
            tmp_bonuse_charas.append({
                'id': charaid,
                'unit': unit,
                'asset': charapicname
            })
        # 对箱活加成角色作额外处理，只对杏二箱(id:37)后箱活作处理，之前的箱活加成角色不用变
        if self.event.id >= 37 and len(set(i['unit'] for i in tmp_bonuse_charas)) == 1:
            for bonuse_chara in tmp_bonuse_charas.copy():
                if bonuse_chara['id'] > 20:
                    tmp_bonuse_charas.remove(bonuse_chara)
            tmp_bonuse_charas.append({
                'unit': tmp_bonuse_charas[0]['unit'],
                'asset': 'vs_90.png'
            })
        self.event.bonusechara = tmp_bonuse_charas

    def _get_gacha_info(self):
        with open(data_path / 'gachas.json', 'r', encoding='utf-8') as f:
            gachas = json.load(f)
        for each_gacha in gachas:
            if not (  # 开服的二三星以及活动报酬卡都是后来才进的卡池，这类卡的来源卡池个人定义为初次登场的卡池
                each_gacha["gachaType"] == 'ceil'
                and each_gacha["name"] != "イベントメンバー出現率UPガチャ"
                and not each_gacha['name'].startswith('[1回限定]')
            ):
                continue
            for each_card in each_gacha["gachaDetails"]:
                if each_card["cardId"] == self.id:
                    self.gacha.id = each_gacha["id"]
                    # gachaCardRarityRateGroupId：
                    # 1天井池和常规池(不清楚怎么区分，暂时靠卡面是否限定区分)、2一去不复返的3星券池子、3fes限、4生日池
                    self.gacha.gachaCardRarityRateGroupId = each_gacha["gachaCardRarityRateGroupId"]
                    self.gacha.name = each_gacha["name"]
                    self.gacha.assetbundleName = each_gacha["assetbundleName"]
                    self.gacha.startAt = datetime.datetime.fromtimestamp(
                        each_gacha['startAt'] / 1000, pytz.timezone('Asia/Shanghai')
                    ).strftime('%Y/%m/%d %H:%M:%S')
                    self.gacha.endAt = datetime.datetime.fromtimestamp(
                        each_gacha["endAt"] / 1000, pytz.timezone('Asia/Shanghai')
                    ).strftime('%Y/%m/%d %H:%M:%S')
                    return

    async def getinfo(self, cardid: int):
        """
        根据卡面id获取卡面信息
        """
        with open(data_path / 'cards.json', 'r', encoding='utf-8') as f:
            allcards = json.load(f)
        for each_card in allcards:
            if each_card["id"] == cardid:
                self.id = each_card["id"]  # 卡面id
                self.characterId = each_card["characterId"]  # 角色id
                self.skillId = each_card["skillId"]  # 技能id

                self.cardRarityType = each_card["cardRarityType"]  # 卡面星数
                self.attr = each_card["attr"]  # 卡面属性
                if each_card.get("supportUnit", "none") != "none":
                    self.unit = each_card["supportUnit"]
                self.prefix = each_card["prefix"]  # 卡面名称
                if each_card["gachaPhrase"] != '-':  # 初始卡无招募语
                    self.gachaPhrase['JP'] = each_card["gachaPhrase"]  # 招募语
                self.cardSkillName['JP'] = each_card["cardSkillName"]  # 技能名称
                self.releaseAt = datetime.datetime.fromtimestamp(
                    each_card['releaseAt'] / 1000, pytz.timezone('Asia/Shanghai')
                ).strftime('%Y/%m/%d %H:%M:%S')  # 发布时间
                self.assets["card"] = each_card["assetbundleName"]  # 卡面大图asset名称
                # 卡面综合力
                for cardparams in each_card["cardParameters"]:
                    self.cardParameters[cardparams["cardParameterType"]] = cardparams["power"]
                break
        # 日文技能效果
        with open(data_path / 'skills.json', 'r', encoding='utf-8') as f:
            skills = json.load(f)
        for each_skill in skills:
            if each_skill["id"] == self.skillId:
                self.cardSkillDes['JP'] = each_skill["description"]
                break

        # 角色名称(日文)、组合名称
        with open(data_path / 'gameCharacters.json', 'r', encoding='utf-8') as f:
            allcards = json.load(f)
        for each_card in allcards:
            if each_card["id"] == self.characterId:
                self.charaName = (
                        each_card.get("firstName", "") + " " + each_card.get("givenName", "")
                ).strip()  # 角色名称
                self.unit = self.unit if self.unit != 'none' else each_card["unit"]  # 组合名称
                break

        # 获取衣装asset名
        with open(data_path / 'cardCostume3ds.json', 'r', encoding='utf-8') as f:
            costume3ds = json.load(f)
        card_costumes_ids = []
        for each_costume in costume3ds:
            if each_costume['cardId'] == self.id:
                card_costumes_ids.append(each_costume["costume3dId"])
        with open(data_path / 'costume3ds.json', 'r', encoding='utf-8') as f:
            costume3ds = json.load(f)
        for each_costume_id in card_costumes_ids:
            for each_model in costume3ds:
                if each_model['id'] == each_costume_id:
                    _parttype = each_model["partType"]
                    if _parttype == 'hair':
                        self.isLimited = True
                    _assetbundleName = each_model["assetbundleName"]
                    self.assets["costume"][_parttype] = self.assets["costume"].get(_parttype, [])
                    self.assets["costume"][_parttype].append(_assetbundleName)
                    break
        # 尝试获取翻译信息
        with open(data_path / 'translate.yaml', encoding='utf-8') as f:
            trans = yaml.load(f, Loader=yaml.FullLoader)
        # 招募语
        try:
            self.gachaPhrase['CN'] = trans['card_gacha_phrase'][self.id]
        except:
            pass
        # 技能名称
        try:
            self.cardSkillName['CN'] = trans['card_skill_name'][self.id]
        except:
            pass
        # 技能效果
        try:
            self.cardSkillDes['CN'] = trans['skill_desc'][self.skillId]
        except:
            pass
        # 最后解析技能效果中的数值
        for key in self.cardSkillDes.keys():
            self.cardSkillDes[key] = cardskill(self.skillId, skills, self.cardSkillDes[key])

        # 获取活动信息
        if self.config.get('event', True):
            try:
                self._get_event_info()
            except:
                pass
        # 获取歌曲信息
        if self.config.get('music', True):
            try:
                self._get_music_info()
            except:
                pass

        # 获取卡池信息
        if self.config.get('gacha', True):
            try:
                self._get_gacha_info()
            except:
                pass

    async def toimg(self) -> 'Image':
        """
        生成卡面的详细信息图
        """
        _tmpcards = [{
            'id': self.id,
            'cardRarityType': self.cardRarityType,
            'assetbundleName': self.assets['card'],
            'attr': self.attr
        }]
        style_color = "#00CCBB"  # 作图的背景色
        left_width = 880  # 左侧图的宽度
        left_pad = (30, 30, 40, 40)  # 左侧图的pad
        right_width = 860   # 右侧图的宽度
        right_pad = (65, 75, 50, 50)  # 右侧图的pad
        _l_w = left_width + left_pad[2] + left_pad[3]
        _r_w = right_width + right_pad[2] + right_pad[3]
        # 生成卡面标题图片title_img
        charaname_img = union(
            [t2i(self.prefix, font_color='white', max_width=int(_r_w/18*13)), t2i(self.charaName, font_color='white')],
            type='row',
            length=0,
            interval=5
        )
        unit_img = Image.open(data_path / f'pics/logo_{self.unit}.png')
        unit_img = unit_img.resize((int(_r_w/18*5), int(_r_w/18*5/unit_img.width*unit_img.height)))
        title_img = union(
            [unit_img, charaname_img],
            type='col',
            length=right_width+40,
            padding=(20,20,30,30),
            interval=35+(right_width-unit_img.width-charaname_img.width)//2,
            align_type='center',
            bk_color=style_color,
            border_type='circle',
            border_radius=_r_w//36
        )
        # 生成卡面详情图片detail_img
        tmp_imgs = []
        # 综合力
        power = sum([self.cardParameters[key] for key in self.cardParameters.keys()])
        tmp_union = union([t2i('综合力'), t2i(str(power))], type='col', length=right_width)
        tmp_imgs.append(tmp_union)
        # 综合力组成
        tmp_paramimgs = []
        tmp_union = union(
            [t2i('演奏'), t2i(str(self.cardParameters['param1']))], type='col', length=right_width
        )
        tmp_paramimgs.append(tmp_union)
        tmp_union = union(
            [t2i('技巧'), t2i(str(self.cardParameters['param2']))], type='col', length=right_width
        )
        tmp_paramimgs.append(tmp_union)
        tmp_union = union(
            [t2i('耐力'), t2i(str(self.cardParameters['param3']))], type='col', length=right_width
        )
        tmp_paramimgs.append(tmp_union)
        tmp_imgs.append(union(tmp_paramimgs, length=0, interval=25, type='row'))
        # 卡面类型
        tmp_union = union(
            [t2i('类型'), t2i('限定' if self.isLimited else '普通')], type='col', length=right_width
        )
        tmp_imgs.append(tmp_union)
        # 技能名
        skillname_img = union(
            [t2i(
                f"{self.cardSkillName[each]}\n({each})", max_width=586, wrap_type='right'
            ) for each in self.cardSkillName.keys()],
            type='row',
            align_type='right',
            length=0,
            interval=10,
        )
        tmp_imgs.append(union(
            [t2i('技能名'), skillname_img], type='col', length=right_width
        ))
        # 技能效果
        skilldes_img = union(
            [t2i(
                f"{self.cardSkillDes[each]}\n({each})",
                max_width=right_width-right_pad[2]-160,
                wrap_type='right'
            ) for each in self.cardSkillDes.keys()],
            type='row',
            align_type='right',
            length=0,
            interval=10
        )
        tmp_imgs.append(union(
            [t2i('技能效果'), skilldes_img], type='col', length=right_width
        ))
        # 招募语
        if len(self.gachaPhrase) > 0:
            gachahrase_img = union(
                [t2i(
                    f"{self.gachaPhrase[each]}\n({each})", max_width=586, wrap_type='right'
                ) for each in self.gachaPhrase.keys()],
                type='row',
                align_type='right',
                length=0,
                interval=10
            )
            tmp_imgs.append(union(
                [t2i('招募语'), gachahrase_img], type='col', length=right_width
            ))
        # 发布时间
        tmp_union = union([t2i('发布时间'), t2i(f'{self.releaseAt}(JP)')], type='col', length=right_width)
        tmp_imgs.append(tmp_union)
        # 卡面缩略图
        if self.cardRarityType in ['rarity_3', 'rarity_4']:
            cardthumnail_pic = union(
                [
                    (await cardthumnail(self.id, False, _tmpcards)).resize((180, 180)),
                    (await cardthumnail(self.id, True, _tmpcards)).resize((180, 180))
                ], type='col', length=0, interval=30)
        else:
            cardthumnail_pic = (await cardthumnail(self.id, False)).resize((180, 180))
        tmp_imgs.append(union([t2i('缩略图'), cardthumnail_pic], type='col', length=right_width))
        # 衣装缩略图
        single_costume_pics = []
        for key in self.assets['costume'].keys():
            for i in self.assets['costume'][key]:
                tmp = (await pjsk_update_manager.get_asset(
                    'startapp/thumbnail/costume', f'{i}.png'
                )).resize((180, 180))
                _type = {'hair': '发型', 'head': '发饰', 'body': '服装'}
                single_costume_pics.append(
                    union([tmp, t2i(_type[key])], type='row', length=0, interval=10)
                )
        _cnt = math.ceil(len(single_costume_pics) / 2)
        if _cnt > 0:
            costume_pic = union(
                single_costume_pics[0: 2], type='col', length=0, interval=30
            )
            for i in range(_cnt-1):
                tmp_union_pic = union(
                    single_costume_pics[i+2: i+4], type='col', length=0, interval=30
                )
                costume_pic = union([costume_pic, tmp_union_pic], type='row', length=0, interval=30)

            tmp_imgs.append(union([t2i('衣装缩略图'), costume_pic], type='col', length=right_width))

        tmp_imgs.append(union([t2i('ID'), t2i(str(self.id))], type='col', length=right_width))

        detail_img = union(
            tmp_imgs,
            type="row",
            interval=43,
            interval_size=3,
            interval_color="#dbdbdb",
            padding=right_pad,
            border_size=3,
            border_color="#a19d9e",
            border_type="circle",
            bk_color='white'
        )

        # 生成卡面大图cardlarge_img
        if self.cardRarityType in ['rarity_3', 'rarity_4']:
            cardlarge_img = union(
                [
                    (await cardlarge(self.id, False, _tmpcards)).resize((_l_w, int(_l_w*0.61))),
                    (await cardlarge(self.id, True, _tmpcards)).resize((_l_w, int(_l_w*0.61))),
                ], type='row', length=0, interval=30)
        else:
            cardlarge_img = (await cardlarge(self.id, False, _tmpcards)).resize((_l_w, int(_l_w*0.61)))

        # 生成gacha大图gacha_img
        gacha_img = None
        if self.gacha.id != 0:
            bannerpic = await pjsk_update_manager.get_asset(
                f'startapp/home/banner/banner_gacha{self.gacha.id}', f'banner_gacha{self.gacha.id}.png'
            )
            bannerpic = bannerpic.resize((left_width, int(left_width / bannerpic.width * bannerpic.height)))
            timepic = union(
                [t2i('开始时间：'+self.gacha.startAt, font_size=25),
                 t2i('结束时间：'+self.gacha.endAt, font_size=25)],
                type='col',
                length=left_width,
            )
            if (  # 若卡面为限定卡，当卡池也为当期池时，认定池子为限定池
                self.isLimited
                and self.gacha.startAt == self.releaseAt
                and self.gacha.gachaCardRarityRateGroupId != 3
            ):
                gachatype = "期间限定"
            else:
                gachatype = {
                    "1": "常规", "3": "fes限定", "4": "生日限定"
                }.get(str(self.gacha.gachaCardRarityRateGroupId), "")
            gachanamepic = union(
                [t2i(self.gacha.name, max_width=left_width), t2i(f"{gachatype}  ID:{self.gacha.id}", font_size=30)],
                type='row',
                length=0,
                interval=10
            )
            gacha_img = union(
                [bannerpic, gachanamepic, timepic],
                type='row',
                padding=left_pad,
                interval=40,
                bk_color='white',
                border_color='#a19d9e',
                border_size=3,
                border_type='circle'
            )

        # 生成event大图event_img
        event_img = None
        if self.event.id != 0:
            bannerpic = await pjsk_update_manager.get_asset(
                f'ondemand/event_story/{self.event.assetbundleName}/screen_image', 'banner_event_story.png'
            )
            bannerpic = bannerpic.resize((left_width, int(left_width / bannerpic.width * bannerpic.height)))
            eventtype = {"marathon": "马拉松(累积点数)", "cheerful_carnival": "欢乐嘉年华(5v5)"}.get(self.event.eventType, "")
            eventnamepic = union(
                [t2i(self.event.name, max_width=left_width), t2i(f"{eventtype}  ID:{self.event.id}", font_size=30)],
                type='row',
                length=0,
                interval=10
            )
            timepic = union(
                [t2i('开始时间：'+self.event.startAt, font_size=30),
                 t2i('结束时间：'+self.event.aggregateAt, font_size=30)],
                type='row',
                length=0,
                interval=40
            )
            bonusechara_pic = []
            for bonusechara in self.event.bonusechara:
                unitcolor = {
                    'piapro': '#000000',
                    'light_sound': '#4455dd',
                    'idol': '#88dd44',
                    'street': '#ee1166',
                    'theme_park': '#ff9900',
                    'school_refusal': '#884499',
                }
                # 活动角色边框显示组合色
                # 这里不是很懂为什么需要经过多次放缩才能让图片锯齿没那么明显，但总之试出来了(ˉ▽ˉ；)...
                _chr_pic = Image.open(data_path / f'chara/{bonusechara["asset"]}').resize((110, 110))
                _bk = Image.new('RGBA', (130, 130), color=unitcolor[bonusechara['unit']])
                _bk.paste(_chr_pic, (10, 10), mask=_chr_pic.split()[-1])
                mask = Image.new("L", _bk.size, 0)
                ImageDraw.Draw(mask).ellipse((1, 1, _bk.size[0] - 2, _bk.size[1] - 2), 255)
                mask = mask.filter(ImageFilter.GaussianBlur(0))
                _bk.putalpha(mask)
                bonusechara_pic.append(_bk.resize((65, 65)).copy())
            charapic = union(bonusechara_pic, type='col', length=0, interval=10)
            attrpic = Image.open(data_path / f'chara/icon_attribute_{self.event.bonuseattr}.png').resize((60, 60))
            _ = union([attrpic, charapic], type='row', interval=10, align_type='right')
            _ = union([timepic, _], type='col', interval=60, length=left_width)
            event_img = union(
                [bannerpic, eventnamepic, _],
                padding=left_pad,
                interval=40,
                type='row',
                bk_color='white',
                border_type='circle',
                border_size=3,
                border_color='#a19d9e'
            )

        # 生成music大图music_img
        music_img = None
        if self.music.id != 0:
            # 图、名称、时间
            jacketpic = await pjsk_update_manager.get_asset(
                fr'startapp/music/jacket/jacket_s_{str(self.music.id).zfill(3)}',
                f'jacket_s_{str(self.music.id).zfill(3)}.png'
            )
            jacketpic = jacketpic.resize((280, 280))

            musicnamepic = t2i(self.music.title, font_size=50, max_width=left_width)
            timepic = t2i('上线时间：' + datetime.datetime.fromtimestamp(
                self.music.publishedAt / 1000, pytz.timezone('Asia/Shanghai')
            ).strftime('%Y/%m/%d %H:%M:%S'))
            _m_w = left_width - 280 - left_pad[2]
            authorpic = union(
                [t2i(f'作词： {self.music.lyricist}', font_size=40, max_width=_m_w),
                t2i(f'作曲： {self.music.composer}', font_size=40, max_width=_m_w),
                t2i(f'编曲： {self.music.arranger}', font_size=40, max_width=_m_w)],
                type='row',
                length=0,
                interval=5,
                align_type='left'
            )
            music_img = union(
                [union(
                    [jacketpic, authorpic],
                    type='col',
                    interval=50,
                    length=left_width
                ), union(
                    [musicnamepic, t2i(f"ID:{self.music.id}", font_size=30)],
                    type='row',
                    interval=10,
                ), timepic],
                type='row',
                interval=40,
                padding=left_pad,
                bk_color='white',
                border_type='circle',
                border_size=3,
                border_color='#a19d9e'
            )

        _interval = 60
        left_imgs = [cardlarge_img]
        right_imgs = [title_img, detail_img]
        # gacha图放在左边
        if gacha_img:
            _k = '当期卡池' if self.releaseAt == self.gacha.startAt else '初次可得卡池'
            _t = t2i(_k,font_size=50,font_color='white')
            _i = Image.new('RGBA', (_l_w, 70))
            ImageDraw.Draw(_i).rounded_rectangle((0, 0, _i.width, _i.height), 25, style_color)
            _i.paste(_t,((_l_w-50*len(_k))//2, 10),mask=_t.split()[-1])
            left_imgs.append(_i.copy())
            left_imgs.append(gacha_img)
        # event图放在左边
        if event_img:
            _t = t2i('活动', font_size=50, font_color='white')
            _i = Image.new('RGBA', (_l_w, 70))
            _d = ImageDraw.Draw(_i)
            _d.rounded_rectangle((0, 0, _i.width, _i.height), 25, style_color)
            _i.paste(_t, ((_l_w-100)//2, 10), mask=_t.split()[-1])
            left_imgs.append(_i.copy())
            left_imgs.append(event_img)
        # music图根据左右侧图长度差距决定放在哪边
        if music_img:
            _i = Image.new('RGBA', (_l_w, 70))
            ImageDraw.Draw(_i).rounded_rectangle((0, 0, _i.width, _i.height), 25, style_color)
            _t = t2i('歌曲', font_size=50, font_color='white')
            _i.paste(_t, ((_l_w-100)//2, 10), mask=_t.split()[-1])
            if (
                sum(i.height for i in left_imgs) + _interval * (len(right_imgs)-1) >
                sum(i.height for i in right_imgs) + _interval * (len(left_imgs)-1) + 80
            ):
                right_imgs.append(_i.copy())
                right_imgs.append(music_img)
            else:
                left_imgs.append(_i.copy())
                left_imgs.append(music_img)
        # 合成左侧图
        left_img = union(
            left_imgs,
            type='row',
            interval=_interval,
            length=_l_w,
            align_type='left',
        )
        # 合成右侧图
        right_img = union(right_imgs, type='row', interval=_interval, align_type='left')
        # 生成最终的info_img
        # info_pad留白，用于自行留下水印
        info_pad = (60, 180)
        info_width = int(sum([left_img.width, right_img.width]) + info_pad[0])
        info_height = int(max([left_img.height, right_img.height]))
        info_img = Image.open(data_path / 'pics/cardinfo.png').resize((info_width+info_pad[0]*2, info_height+info_pad[1]*2))
        info_img.paste(left_img, info_pad, mask=left_img.split()[-1])
        info_img.paste(right_img, (left_img.width + info_pad[0]*2, info_pad[1]), mask=right_img.split()[-1])

        badge_img = Image.open(data_path / 'pics/cardinfo_badge.png')
        badge_img = badge_img.resize((right_img.width//2, int(badge_img.height/badge_img.width*right_img.width//2)))
        info_img.paste(badge_img, (info_pad[0], int(info_pad[1]/3*2 - badge_img.height)), mask=badge_img.split()[-1])
        # watermark_img = t2i('Code by Yozora&Watagashi_uni\nGenerated by Unibot', font_size=35, font_color=style_color)
        # info_img.paste(
        #     watermark_img,
        #     (info_img.width-watermark_img.width-info_pad[0], info_img.height-watermark_img.height-info_pad[1]//6),
        #     mask=watermark_img.split()[-1]
        # )
        return info_img
