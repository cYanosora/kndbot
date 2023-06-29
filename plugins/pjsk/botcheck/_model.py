from services.db_context import db
from configs.path_config import RESOURCE_PATH
from pathlib import Path
try:
    import ujson as json
except:
    import json


class PjskUnibotQQManager:

    def __init__(self, file: Path):
        self.starttime = 0
        self.file = file
        self._data: dict = {'unibot': []}
        if file.exists():
            with open(file, "r", encoding="utf8") as f:
                self._data: dict = json.load(f)

    def _save_data(self):
        with open(self.file, "w", encoding="utf8") as f:
            json.dump(self._data, f, indent=4)

    def get(self, user_qq: int):
        return True if user_qq in self._data['unibot'] else False

    def getall(self):
        return self._data['unibot']

    def set(self, user_qq: int):
        if user_qq not in self._data['unibot']:
            self._data['unibot'].append(user_qq)
            self._save_data()

    def pop(self, user_qq: int):
        if user_qq in self._data['unibot']:
            self._data['unibot'].remove(user_qq)
            self._save_data()


unibot = PjskUnibotQQManager(RESOURCE_PATH / 'masterdata' / 'unibot.json')


class PjskUniRecord(db.Model):
    __tablename__ = "pjsk_uni_record"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    count = db.Column(db.BigInteger(), default=0, nullable=False)

    @classmethod
    async def get_record(cls, rate: float = 0.5, is_reverse: bool = False):
        """
        说明：
            按记录占比获取用户账号列表
        参数：
            :param rate: 占比，默认50%
            :param is_reverse: 开启时，获取低于rate的账号；关闭时，获取高于rate的账号
        """
        querys = await cls.query.gino.all()
        result = []
        max_count = max(q.count for q in querys)
        sum_count = sum(q.count for q in querys)
        if is_reverse:
            for i in querys:
                if i.count / max_count < rate:
                    result.append(i.user_qq)
        else:
            for i in querys:
                if i.count / max_count > rate:
                    result.append(i.user_qq)
        return result, sum_count

    @classmethod
    async def add(cls, user_qq: int):
        """
        说明：
            添加次数
        参数：
            :param user_qq: qq号
        """
        user = await cls.get(user_qq)
        await user.update(count=user.count+1).apply()

    @classmethod
    async def get(cls,user_qq: int):
        """
        说明：
            获取用户信息
        参数：
            :param user_qq: qq号
        """
        user = await cls.query.where(cls.user_qq == user_qq).gino.first()
        return user or await cls.create(user_qq=user_qq, count=0)

    @classmethod
    async def pop(cls,user_qq: int):
        """
        说明：
            删除用户信息
        参数：
            :param user_qq: qq号
        """
        user = await cls.query.where(cls.user_qq == user_qq).gino.first()
        await user.delete()


