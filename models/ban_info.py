from typing import Optional
from services.db_context import db
import time


class BanInfo(db.Model):
    __tablename__ = "ban_info"

    id = db.Column(db.BigInteger(), nullable=False, primary_key=True)
    user_id = db.Column(db.BigInteger(), nullable=True)
    group_id = db.Column(db.BigInteger(), nullable=True)
    type = db.Column(db.Text(), nullable=False)     # group/user/all/plugin_name
    ban_level = db.Column(db.Integer(), nullable=False)
    ban_time = db.Column(db.BigInteger())
    duration = db.Column(db.BigInteger())

    @classmethod
    async def check_ban_level(cls, user_id: int, level: int) -> bool:
        """
        说明：
            检测ban掉目标的用户与unban用户的权限等级大小，同级以下不可解禁，返回真值
        参数：
            :param user_id: unban用户的qq号
            :param level: ban掉目标用户的权限等级
        """
        user = await cls.query.where((cls.user_id == user_id) & (cls.type != "group")).gino.first()
        if not user:
            return False
        if user.ban_level > level:
            return True
        return False

    @classmethod
    async def check_ban_time(cls, user_id: Optional[int] = None, group_id: Optional[int] = None) -> str:
        """
        说明：
            检测用户/群被ban时长\n
            qq号+群号：用户在此群内被ban时长\n
            仅qq号：用户全局被ban时长\n
            仅群号：群被ban时长
        参数：
            :param user_id: qq号
            :param group_id: 群号
        """
        return await cls._get_ban_time(user_id, group_id)

    @classmethod
    async def is_ban(cls, user_id: Optional[int] = None, group_id: Optional[int] = None) -> bool:
        """
        说明：
            判断用户/群是否被ban\n
            qq号+群号：用户在此群内是否被ban\n
            仅qq号：用户是否被ban\n
            仅群号：群是否被ban
        参数：
            :param user_id: qq号
            :param group_id: 群号
        """
        if user_id is None and group_id is None:
            return False
        if await cls.check_ban_time(user_id=user_id, group_id=group_id):
            return True
        else:
            await cls.unban(user_id=user_id, group_id=group_id)
            return False

    @classmethod
    async def is_super_ban(cls, user_id: int) -> bool:
        """
        说明：
            判断用户是否被超管ban
        参数：
            :param user_id: qq号
        """
        user = await cls.query.where((cls.user_id == user_id) & (cls.type == "all")).gino.first()
        if not user:
            return False
        if user.ban_level == 9:
            return True

    @classmethod
    async def ban(
            cls,
            ban_level: int,
            duration: int,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None,
    ) -> bool:
        """
        说明：
            ban掉目标用户\n
            qq号+群号：仅对应群ban掉此用户\n
            仅qq号：全局ban掉此用户\n
            仅群号：ban掉此群
        参数：
            :param user_id: 目标用户qq号
            :param group_id: 目标群号
            :param ban_level: 使用ban命令用户的权限，9为超管级别
            :param duration:  ban时长(秒)，-1为无限期
        """
        return await cls._ban(ban_level, duration, user_id, group_id)

    @classmethod
    async def unban(
            cls,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None
    ) -> bool:
        """
        说明：
            unban用户/群\n
            qq号+群号：解禁对应群对应用户\n
            仅qq号：解禁此用户\n
            仅群号：解禁此群
        参数：
            :param user_id: qq号
            :param group_id: 群号
        """
        return await cls._unban(user_id, group_id)

    @classmethod
    async def is_plugin_ban(cls, module: str, user_id: Optional[int] = None, group_id: Optional[int] = None) -> bool:
        """
        说明：
            判断用户/群是否被ban插件\n
            qq号+群号：用户在此群内是否被ban插件\n
            仅qq号：用户是否被ban插件\n
            仅群号：群是否被ban插件
        参数：
            :param module: 插件名
            :param user_id: qq号
            :param group_id: 群号
        """
        if user_id is None and group_id is None:
            return False
        if await cls.check_plugin_ban_time(module, user_id=user_id, group_id=group_id):
            return True
        else:
            await cls.unban_plugin(module, user_id=user_id, group_id=group_id)
            return False

    @classmethod
    async def check_plugin_ban_time(cls, module: str, user_id: Optional[int] = None, group_id: Optional[int] = None) -> str:
        """
        说明：
            检测用户/群被ban时长\n
            qq号+群号：用户在此群内被ban时长\n
            仅qq号：用户全局被ban时长\n
            仅群号：群被ban时长
        参数：
            :param module: 插件名
            :param user_id: qq号
            :param group_id: 群号
        """
        return await cls._get_ban_time(user_id, group_id, module)

    @classmethod
    async def ban_plugin(
            cls,
            module: str,
            ban_level: int,
            duration: int,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None,
    ) -> bool:
        """
        说明：
            ban掉目标用户的插件使用权限\n
            qq号+群号：仅对应群ban掉此用户的插件使用权限\n
            仅qq号：全局ban掉此用户的插件使用权限\n
            仅群号：ban掉此群的插件使用权限
        参数：
            :param module: 插件名
            :param user_id: 目标用户qq号
            :param group_id: 目标群号
            :param ban_level: 使用ban命令用户的权限
            :param duration:  ban时长(秒)，为-1时为无限期
        """
        return await cls._ban(ban_level, duration, user_id, group_id, module)

    @classmethod
    async def unban_plugin(
            cls,
            module: str,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None
    ) -> bool:
        """
        说明：
            unban用户/群的插件限制\n
            qq号+群号：解禁对应群对应用户的插件限制\n
            仅qq号：解禁此用户的插件限制\n
            仅群号：解禁此群的插件限制
        参数：
            :param module: 插件名
            :param user_id: qq号
            :param group_id: 群号
        """
        return await cls._unban(user_id, group_id, module)

    @classmethod
    async def _get_ban_time(
            cls,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None,
            module: Optional[str] = None
    ) -> str:
        """
        说明：
            检测用户/群被ban时长\n
            qq号+群号：用户在此群内被ban时长\n
            仅qq号：用户全局被ban时长\n
            仅群号：群被ban时长
            参数 module 存在时，检测对象为插件
        参数：
            :param user_id: qq号
            :param group_id: 群号
            :param module: 插件名
        """
        if user_id is not None and group_id is not None:
            type = module or "user"
            query = cls.query.where(
                (cls.user_id == user_id) & (cls.group_id == group_id) & (cls.type == type)
            )
        elif user_id is not None:
            type = module or "all"
            query = cls.query.where((cls.user_id == user_id) & (cls.type == type))
        elif group_id is not None:
            type = module or "group"
            query = cls.query.where((cls.group_id == group_id) & (cls.type == type))
        else:
            return ""
        target = await query.gino.first()
        if not target:
            return ""
        if target.duration == -1:
            return "∞"
        if time.time() > (target.ban_time + target.duration):
            return ""
        return target.ban_time + target.duration - time.time()

    @classmethod
    async def _unban(
            cls,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None,
            module: Optional[str] = None
    ) -> bool:
        """
        说明：
            unban用户/群\n
            qq号+群号：解禁对应群对应用户\n
            仅qq号：解禁此用户\n
            仅群号：解禁此群
            参数 module 存在时，检测对象为插件
        参数：
            :param user_id: qq号
            :param group_id: 群号
            :param module: 插件名
        """
        if user_id is not None and group_id is not None:
            type = module or "user"
            query = cls.query.where(
                (cls.user_id == user_id) & (cls.group_id == group_id) & (cls.type == type)
            )
        elif user_id is not None:
            type = module or "all"
            query = cls.query.where(
                (cls.user_id == user_id) & (cls.type == type)
            )
        elif group_id is not None:
            type = module or "group"
            query = cls.query.where(
                (cls.group_id == group_id) & (cls.type == type)
            )
        else:
            return False
        query = query.with_for_update()
        target = await query.gino.first()
        if target is None:
            return False
        else:
            await target.delete()
            return True

    @classmethod
    async def _ban(
            cls,
            ban_level: int,
            duration: int,
            user_id: Optional[int] = None,
            group_id: Optional[int] = None,
            module: Optional[str] = None
    ) -> bool:
        """
        说明：
            ban掉目标用户\n
            qq号+群号：仅对应群ban掉此用户\n
            仅qq号：全局ban掉此用户\n
            仅群号：ban掉此群
            参数 module 存在时，检测对象为插件
        参数：
            :param ban_level: 使用ban命令用户的权限，为9时为超管权限
            :param duration:  ban时长(秒)，为-1时为无限期
            :param user_id: 目标用户qq号
            :param group_id: 目标群号
            :param module: 插件名
        """
        if user_id is not None and group_id is not None:
            type = module or "user"
            query = cls.query.where(
                (cls.user_id == user_id) & (cls.group_id == group_id) & (cls.type == type)
            )
        elif user_id is not None:
            type = module or "all"
            query = cls.query.where(
                (cls.user_id == user_id) & (cls.type == type)
            )
        elif group_id is not None:
            type = module or "group"
            query = cls.query.where(
                (cls.group_id == group_id) & (cls.type == type)
            )
        else:
            return False

        query = query.with_for_update()
        target = await query.gino.first()
        if not await cls._get_ban_time(user_id, group_id, module):
            await cls._unban(user_id, group_id, module)
            target = None
        if target is None:
            await cls.create(
                user_id=user_id,
                group_id=group_id,
                type=type,
                ban_level=ban_level,
                ban_time=time.time(),
                duration=duration,
            )
            return True
        else:
            return False