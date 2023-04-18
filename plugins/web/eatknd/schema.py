import calendar
from datetime import datetime, timedelta
from models.friend_user import FriendUser
from services.db_context import db
from typing import Optional, List
from models.group_member_info import GroupInfoUser
import secrets
import string


def filter_data_by_type(data, type: str):
    if type == 'day':
        data = [i for i in data if (datetime.now().date() - i.time.date()).days == 0]
    elif type == 'week':
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).date()
        week_end = (now + timedelta(days=6 - now.weekday())).date()
        data = [i for i in data if week_start < i.time.date() < week_end]
    elif type == 'month':
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1).date()
        month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1]).date()
        data = [i for i in data if month_start <= i.time.date() <= month_end]
    return data


class EatkndRecord(db.Model):
    __tablename__ = "eatknd_record"
    
    id = db.Column(db.BigInteger(), primary_key=True)

    user_id = db.Column(db.BigInteger(), nullable=False)
    type = db.Column(db.String(), nullable=False)

    score = db.Column(db.Integer(), default=0)
    time = db.Column(db.DateTime(), default=0)
    attempts = db.Column(db.Integer(), nullable=False, default=0)

    nickname = db.Column(db.Unicode(), default='')
    message = db.Column(db.Unicode(), nullable=False, default='')

    system = db.Column(db.String(), default='')
    area = db.Column(db.String(), default='')

    @classmethod
    async def get(cls, user_id: int, type: str) -> Optional["EatkndRecord"]:
        query = cls.query.where((cls.user_id == user_id) & (cls.type == type))
        query = cls._join_with_username(query)
        user = await query.gino.first()
        return user
    
    @classmethod
    async def set(
        cls, user_id: int,
        type: str, score: int, 
        nickname: str = "", message: str = "",
        system: str = "", area: str = "", 
    ):
        user = await cls.get(user_id, type)
        if not user:
            await cls.create(
                user_id=user_id, type=type,
                score=score, time=datetime.now(), attempts=1,
                nickname=nickname, message=message, 
                system=system, area=area,
            )
        else:
            await user.update(
                score=max(user.score, score), time=datetime.now(), attempts=user.attempts + 1,
                nickname=nickname or user.nickname, message=message or user.message, 
                system=system or user.system, area=area or user.area,
            ).apply()

    @classmethod
    async def get_list(cls, type: str, num: int = 10, offset: int = 0, reverse: bool = True, is_update: bool = False) -> List["EatkndRecord"]:
        query = cls.query.where((cls.type == type) & (cls.score > 0))
        if not is_update:
            query = cls._join_with_username(query)
        data = list(await query.gino.all())
        data = filter_data_by_type(data, type)
        data.sort(key=lambda x: x.score, reverse=reverse)
        total = len(data)
        if total == 0:
            return []
        elif offset >= total:
            return data[-1]
        else:
            return data[offset: offset+num]

    @classmethod
    async def get_len(cls, type: str) -> int:
        query = cls.query.where((cls.type == type) & (cls.score > 0))
        data = list(await query.gino.all())
        data = filter_data_by_type(data, type)
        return len(data)

    @classmethod
    async def query_user(cls, type: str, name: str, is_fuzzy: bool = False, reverse: bool = True) -> List["EatkndRecord"]:
        query = cls.query.where((cls.type == type) & (cls.score > 0))
        query = cls._join_with_username(query)
        data = list(await query.gino.all())
        data = filter_data_by_type(data, type)
        data.sort(key=lambda x: x.score, reverse=reverse)
        return [
            i for i in data
            if (
                (i.username == name or i.nickname == name)
                if not is_fuzzy
                else (name.lower() in i.username.lower() or name.lower() in i.nickname.lower())
            )
        ]

    @classmethod
    def _join_with_username(cls, query):
        subquery_alias = query.alias('subq')
        query = db.select(
            [subquery_alias, GroupInfoUser.user_name.label('username')]
        ).select_from(subquery_alias.outerjoin(
            FriendUser.user_id == subquery_alias.c.user_id,
        ))
        return query


class EatkndToken(db.Model):
    __tablename__ = "eatknd_token"

    id = db.Column(db.BigInteger(), primary_key=True)
    user_id = db.Column(db.BigInteger(), nullable=False)
    token = db.Column(db.String(), nullable=False)
    _idx1 = db.Index("eatknd_token_idx1", "user_id", "token", unique=True)

    @classmethod
    async def get_user_by_id(cls, user_id: int) -> "EatkndToken":
        query = cls.query.where(cls.user_id == user_id)
        user = await query.gino.first()
        return user

    @classmethod
    async def get_user_by_token(cls, token: str) -> Optional["EatkndToken"]:
        query = cls.query.where(cls.token == token)
        user = await query.gino.first()
        return user

    @classmethod
    async def gene_token(cls, user_id: int) -> str:
        def random_token() -> str:
            alphabet = string.ascii_letters + string.digits
            random_string = ''.join(secrets.choice(alphabet) for _ in range(16))
            return random_string
        token = random_token()
        tokens = await cls.get_all_tokens()
        while token in tokens:
            token = random_token()
        user = await cls.get_user_by_id(user_id)
        if user:
            await user.update(token=token).apply()
        else:
            await cls.create(user_id=user_id, token=token)
        return token

    @classmethod
    async def get_all_tokens(cls):
        return await cls.select("token").gino.all()


