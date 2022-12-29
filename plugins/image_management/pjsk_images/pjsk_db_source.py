from datetime import datetime
from services.db_context import db
from typing import List, Tuple, Union, Optional


class PjskAlias(db.Model):
    __tablename__ = "pjsk_alias"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode(), nullable=False)
    alias = db.Column(db.Unicode(), nullable=False)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    join_time = db.Column(db.DateTime(), nullable=False)
    is_pass = db.Column(db.Boolean(), default=False)

    @classmethod
    async def add_alias(
            cls,
            name: str,
            alias: str,
            user_qq: int,
            group_id: int,
            join_time: datetime,
            is_pass: bool
    ) -> bool:
        """
        说明：
            添加别名，全局昵称仅可添加一次，群内昵称互相独立
        参数：
            :param name: 主名
            :param user_qq: qq号
            :param group_id: 群号
            :param alias: 别名
            :param join_time: 添加时间
            :param is_pass: True代表全局昵称，False代表群内昵称
        """
        # 若为全局首次添加昵称，添加后删除所有群内特有同名昵称
        if is_pass and not await cls.check_alias_exists(alias):
            await cls.create(
                name=name, user_qq=user_qq, group_id=group_id,
                alias=alias, is_pass=is_pass, join_time=join_time
            )
            await cls.delete.where((cls.alias == alias) & (cls.is_pass == False)).gino.status()
            return True
        # 若为群内首次添加昵称
        elif not is_pass and not await cls.check_alias_exists(alias, group_id=group_id):
            await cls.create(
                name=name, user_qq=user_qq, group_id=group_id,
                alias=alias, is_pass=is_pass, join_time=join_time
            )
            return True
        return False

    @classmethod
    async def delete_alias(cls, alias: str, group_id: Optional[int] = None) -> bool:
        """
        说明：
            删除别名
            有群号时：先检测群内有无别名，没有则删除全局别名
            无群号时：删除全局别名
        参数：
            :param alias: 别名
            :param group_id: 群号
        """
        if group_id and await cls.check_alias_exists(alias, group_id):
            query = cls.query.where((cls.alias == alias) & (cls.group_id == group_id))
            query = await query.gino.first()
            await query.delete()
            return True
        elif await cls.check_alias_exists(alias):
            query = cls.query.where((cls.alias == alias) & (cls.is_pass == True))
            query = await query.gino.first()
            await query.delete()
            return True
        else:
            return False

    @classmethod
    async def check_alias_exists(cls, alias: str, group_id: Optional[int] = None) -> bool:
        """
        说明：
            检测别名是否已存在，有群号仅检测群内，无群号检测全局
        参数：
            :param alias: 别名
            :param group_id: 群号
        """
        if group_id:
            query = await cls.query.where(cls.group_id == group_id).gino.all()
            query = [res.alias for res in query]
        else:
            query = await cls.query.where(cls.is_pass == True).gino.all()
            query = [res.alias for res in query]
        if alias in query:
            return True
        return False

    @classmethod
    async def check_name_exists(cls, name: str) -> bool:
        """
        说明：
            检测主名是否已存在
        参数：
            :param name: 主名
        """
        query = await cls.select("name").gino.all()
        query = set(res[0] for res in query)
        if name in query:
            return True
        return False

    @classmethod
    async def query_name(
            cls,
            alias: str,
            fuzzy_search: bool = False,
            group_id: Optional[int] = None
    ) -> Union[str, Tuple[str, str]]:
        """
        说明：
            查找对应别名的主名
        参数：
            :param alias: 别名, fuzzy_search为True时代表接收开头包含别名的文本
            :param fuzzy_search: 是否使用模糊搜索
            :param group_id: 群号，有群号时先查询群内昵称，再查询全局昵称，无群号时只查询全局昵称
        返回：
            :return :fuzzy_search开启时，以元组形式返回(主名, 别名之后的多余文本)
        """
        if not fuzzy_search:
            if not group_id:
                query = await cls.select("name").where(cls.alias == alias).gino.scalar()
                return query
            else:
                query = await cls.select("name").where(
                    (cls.alias == alias) & (cls.group_id == group_id)
                ).gino.scalar()
                if not query:
                    query = await cls.select("name").where(
                        (cls.alias == alias) & (cls.is_pass == True)
                    ).gino.scalar()
                return query
        else:
            if not group_id:
                querys = await cls.select("alias").gino.all()
                querys = sorted([res[0] for res in querys], key=len, reverse=True)
                for each in querys:
                    if alias.startswith(each):
                        name = await cls.select("name").where(cls.alias == each).gino.scalar()
                        return name, alias[len(each):].strip()
                return "", ""
            else:
                querys = await cls.select("alias").where(
                    (cls.group_id == group_id) | (cls.is_pass == True)
                ).gino.all()
                querys = sorted([res[0] for res in querys], key=len, reverse=True)
                for each in querys:
                    if alias.startswith(each):
                        name = await cls.select("name").where(
                            (cls.alias == each) & ((cls.group_id == group_id) | (cls.is_pass == True))
                        ).gino.scalar()
                        return name, alias[len(each):].strip()
                return "", ""

    @classmethod
    async def query_alias(cls, name: str, group_id: Optional[int] = None) -> List[str]:
        """
        说明：
            查找对应主名的所有别名
        参数：
            :param name: 主名
            :param group_id: 群号，有群号时查询仅在群内使用的别名，无群号时查询查询全局别名
        """
        if not group_id:
            query = await cls.select("alias").where((cls.name == name) & (cls.is_pass == True)).gino.all()
        else:
            query = await cls.select("alias").where(
                (cls.name == name) & (cls.group_id == group_id) & (cls.is_pass == False)
            ).gino.all()
        query = [res.alias for res in query]
        return query
