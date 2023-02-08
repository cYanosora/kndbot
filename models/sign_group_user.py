from datetime import datetime
from typing import List, Optional
from services.db_context import db


class SignGroupUser(db.Model):
    __tablename__ = "sign_group_users"

    id = db.Column(db.Integer(), primary_key=True)   # 自增id
    user_qq = db.Column(db.BigInteger(), nullable=False)   # QQ号
    group_id = db.Column(db.BigInteger(), nullable=False)   # 群号
    checkin_count = db.Column(db.Integer(), nullable=False)   # 签到次数
    checkin_time_last = db.Column(db.DateTime(timezone=True), nullable=False)   # 上次签到时间
    impression = db.Column(db.Numeric(scale=3, asdecimal=False), nullable=False)   # 好感度
    add_probability = db.Column(
        db.Numeric(scale=3, asdecimal=False), nullable=False, default=0
    )   # 额外一次性好感双倍概率
    extra_impression = db.Column(
        db.Numeric(scale=3, asdecimal=False), nullable=False, default=0
    )   # 额外一次性好感加成
    custom_level = db.Column(db.Integer(), nullable=True)   # 自定义好感度等级
    sign_items = db.Column(db.JSON(), nullable=False, default={})   # 一次性签到道具
    continued_sign_items = db.Column(db.JSON(), nullable=False, default={})  # 持续性签到道具
    impression_promoted_time = db.Column(
        db.DateTime(timezone=True), nullable=False, default=datetime.min
    )  # 好感度等级加成时间
    _idx1 = db.Index("sign_group_users_idx1", "user_qq", "group_id", unique=True)   # 约束

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
            sign_items = {},     # 一次性签到道具
            continued_sign_items = {}   # 持续性签到道具
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
    async def get_all_users(cls, group_id: Optional[int] = None) -> List["SignGroupUser"]:
        """
        说明:
            获取所有签到数据
        参数:
            :param group_id: 群号
        """
        if not group_id:
            query = await cls.query.gino.all()
        else:
            query = await cls.query.where((cls.group_id == group_id)).gino.all()
        return query

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
        items = user.continued_sign_items
        for p in items.copy():
            items[p] -= 1
            if items[p] <= 0:
                del items[p]
        await user.update(
            checkin_count=user.checkin_count + 1,
            checkin_time_last=checkin_time_last,
            impression=user.impression + impression,
            add_probability=0,
            extra_impression=0,
            sign_items={},
            continued_sign_items=items
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
            async with db.transaction():
                await user1.update(group_id=114514).apply()
                await user2.update(group_id=src_group_id).apply()
                await user1.update(group_id=tar_group_id).apply()

    @classmethod
    async def add_property(
        cls,
        user_qq: int,
        group_id: int,
        name: str,
        num: int = 1,
        max: int = 0,
        disposable: bool = True
    ):
        """
        说明：
            增加签到道具
        参数：
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
            :param num: 增加数量
            :param max: 所持道具数量上限, 0为无上限
            :param disposable: 签到道具是否为一次性，默认是
        """
        query = cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id))
        query = query.with_for_update()
        user = await query.gino.first()
        if user:
            if disposable:
                p = user.sign_items
            else:
                p = user.continued_sign_items
            if p.get(name) is None:
                p[name] = num
            elif max == 0 or p[name] < max:
                p[name] += num
            if disposable:
                await user.update(sign_items=p).apply()
            else:
                await user.update(continued_sign_items=p).apply()
        else:
            if disposable:
                await cls.create(
                    user_qq=user_qq,
                    group_id=group_id,
                    checkin_count=0,
                    checkin_time_last=datetime.min,  # 从未签到过
                    impression=0,
                    custom_level=-1,
                    sign_items={name: num},
                    continused_sign_items={},
                )
            else:
                await cls.create(
                    user_qq=user_qq,
                    group_id=group_id,
                    checkin_count=0,
                    checkin_time_last=datetime.min,  # 从未签到过
                    impression=0,
                    custom_level=-1,
                    sign_items={},
                    continued_sign_items={name: num}
                )

    @classmethod
    async def sub_property(cls, user_qq: int, group_id: int, name: str, num: int = 1, disposable: bool = True):
        """
        说明：
            减少签到道具
        参数：
            :param user_qq: qq号
            :param group_id: 所在群号
            :param name: 道具名称
            :param num: 减少数量
            :param disposable: 签到道具是否为一次性，默认是
        """
        query = cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id))
        query = query.with_for_update()
        user = await query.gino.first()
        if user:
            if disposable:
                p = user.sign_items
                if name in p:
                    p[name] -= num
                    if p[name] <= 0:
                        del p[name]
                    await user.update(sign_items=p).apply()
                    print(p)
                    return True
            else:
                p = user.continued_sign_items
                if name in p:
                    p[name] -= num
                    if p[name] <= 0:
                        del p[name]
                    await user.update(continued_sign_items=p).apply()
                    return True
        else:
            await cls.create(
                user_qq=user_qq,
                group_id=group_id,
                checkin_count=0,
                checkin_time_last=datetime.min,  # 从未签到过
                impression=0,
                custom_level=-1,
                sign_items={},
                continued_sign_items={}
            )