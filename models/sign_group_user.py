from datetime import datetime
from typing import List
from services.db_context import db


class SignGroupUser(db.Model):
    __tablename__ = "sign_group_users"

    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    checkin_count = db.Column(db.Integer(), nullable=False)
    checkin_time_last = db.Column(db.DateTime(timezone=True), nullable=False)
    impression = db.Column(db.Numeric(scale=3, asdecimal=False), nullable=False)
    add_probability = db.Column(
        db.Numeric(scale=3, asdecimal=False), nullable=False, default=0
    )
    extra_impression = db.Column(
        db.Numeric(scale=3, asdecimal=False), nullable=False, default=0
    )
    custom_level = db.Column(db.Integer(), nullable=True)
    sign_items = db.Column(db.JSON(), nullable=False, default={})
    impression_promoted_time = db.Column(
        db.DateTime(timezone=True), nullable=False, default=datetime.min
    )
    _idx1 = db.Index("sign_group_users_idx1", "user_qq", "group_id", unique=True)

    @classmethod
    async def ensure(
            cls, user_qq: int, group_id: int, for_update: bool = False
    ) -> "SignGroupUser":
        """
        说明:
            获取签到用户
        参数:
            :param user_qq: 用户qq
            :param group_id: 所在群聊
            :param for_update: 是否存在修改数据
        """
        query = cls.query.where(
            (cls.user_qq == user_qq) & (cls.group_id == group_id)
        )
        if for_update:
            query = query.with_for_update()
        user = await query.gino.first()
        return user or await cls.create(
            user_qq=user_qq,
            group_id=group_id,
            checkin_count=0,
            checkin_time_last=datetime.min,  # 从未签到过
            impression=0,
            custom_level=-1,
            sign_items = {}
        )

    @classmethod
    async def get_user_all_data(cls, user_qq: int) -> List["SignGroupUser"]:
        """
        说明:
            获取某用户所有数据
        参数:
            :param user_qq: 用户qq
        """
        query = cls.query.where(cls.user_qq == user_qq)
        db.session.commit()
        query = query.with_for_update()
        return await query.gino.all()

    @classmethod
    async def sign(cls, user: "SignGroupUser", impression: float, checkin_time_last: datetime):
        """
        说明:
            签到
        说明:
            :param user: 用户
            :param impression: 增加的好感度
            :param checkin_time_last: 签到时间
        """
        await user.update(
            checkin_count=user.checkin_count + 1,
            checkin_time_last=checkin_time_last,
            impression=user.impression + impression,
            add_probability=0,
            extra_impression=0,
            sign_items={}
        ).apply()

    @classmethod
    async def get_all_impression(cls, group_id: int) -> "list, list, list":
        """
        说明：
            获取该群所有用户 id 及对应 好感度
        参数：
            :param group_id: 群号
        """
        impression_list = []
        user_qq_list = []
        user_group = []
        if group_id:
            query = cls.query.where(cls.group_id == group_id)
        else:
            query = cls.query
        for user in await query.gino.all():
            impression_list.append(user.impression)
            user_qq_list.append(user.user_qq)
            user_group.append(user.group_id)
        return user_qq_list, impression_list, user_group

    @classmethod
    async def get_user_in_group_impr(cls, user_qq: int, group_id: int) -> float:
        """
        说明:
            获取某用户在某群的好感度
        参数:
            :param user_qq: 用户qq
            :param group_id: 用户所在群号
        """
        impr = await cls.select("impression").where((cls.user_qq == user_qq) & (cls.group_id == group_id)).gino.scalar()
        return impr

    @classmethod
    async def setlevel(
            cls, user_qq: int, group_id: int, level: int
    ):
        """
        说明:
            设置某用户某群的好感度等级
        参数:
            :param user_qq: 用户qq
            :param group_id: 用户所在群号
            :param level: 用户设置的好感度等级
        """
        user = await cls.ensure(user_qq, group_id)
        await user.update(
            custom_level=level
        ).apply()

    @classmethod
    async def exchange_user_data(cls, user_qq: int, src_group_id: int, tar_group_id: int):
        """
        说明:
            交换某用户两个所在群的签到数据
        参数:
            :param user_qq: 用户qq
            :param src_group_id: 来源群号
            :param tar_group_id: 目标群号
        """
        if src_group_id != tar_group_id:
            user1 = await cls.ensure(user_qq, src_group_id)
            user2 = await cls.ensure(user_qq, tar_group_id)
            if not user1 or not user2:
                raise ValueError("无此签到信息")
            await user1.update(group_id=114514).apply()
            await user2.update(group_id=src_group_id).apply()
            await user1.update(group_id=tar_group_id).apply()

    @classmethod
    async def add_property(cls, user_qq: int, group_id: int, name: str, max: int = 0):
        """
        说明：
            增加签到道具
        参数：
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
            :param max: 所持道具数量上限, 0为无上限
        """
        query = cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id))
        query = query.with_for_update()
        user = await query.gino.first()
        if user:
            p = user.sign_items
            if p.get(name) is None:
                p[name] = 1
            elif max == 0 or p[name] < max:
                p[name] += 1
            await user.update(sign_items=p).apply()
        else:
            await cls.create(
                user_qq=user_qq,
                group_id=group_id,
                checkin_count=0,
                checkin_time_last=datetime.min,  # 从未签到过
                impression=0,
                custom_level=-1,
                sign_items={name: 1}
            )

    @classmethod
    async def sub_property(cls, user_qq: int, group_id: int, name: str):
        """
        说明：
            减少签到道具
        参数：
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
        """
        query = cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id))
        query = query.with_for_update()
        user = await query.gino.first()
        if user:
            p = user.sign_items
            if p.get(name, 0) > 0:
                p[name] -= 1
            await user.update(sign_items=p).apply()
        else:
            await cls.create(
                user_qq=user_qq,
                group_id=group_id,
                checkin_count=0,
                checkin_time_last=datetime.min,  # 从未签到过
                impression=0,
                custom_level=-1,
                sign_items={}
            )