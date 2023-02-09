from datetime import datetime
from services.db_context import db
from typing import Optional, Union


class ImageUpload(db.Model):
    __tablename__ = "image_upload"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer(), primary_key=True)
    gallery = db.Column(db.Unicode(), nullable=False)
    image_id = db.Column(db.Integer(), nullable=False)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    join_time = db.Column(db.DateTime(), nullable=False)
    is_record = db.Column(db.Boolean(), nullable=False, default=0)

    _idx1 = db.Index("image_upload_idx1", "gallery", "image_id", unique=True)

    @classmethod
    async def add_record(
        cls,
        gallery: str,
        image_id: int,
        user_qq: int,
        group_id: int,
        is_record: bool = False
    ) -> bool:
        """
        说明：
            添加记录
        参数：
            :param gallery: 图库名
            :param image_id: 图片id
            :param user_qq: qq号
            :param group_id: 群号
            :param is_record: 是否记录到同人图库
        返回：
            :returns: 若成功添加记录，返回True
        """
        if await cls.check_exists(gallery, image_id):
            return False
        await cls.create(
            gallery=gallery,
            image_id=image_id,
            user_qq=user_qq,
            group_id=group_id,
            join_time=datetime.now(),
            is_record=is_record
        )
        return True

    @classmethod
    async def del_record(cls, gallery: str, image_id: int) -> bool:
        """
        说明：
            删除记录
        参数：
            :param gallery: 图库名
            :param image_id: 图片id
        返回：
            :returns: 若成功删除记录，返回True
        """
        query = await cls.query.where(
            (cls.gallery == gallery) & (cls.image_id == image_id)
        ).gino.first()
        if query:
            await query.delete()
            return True
        return False

    @classmethod
    async def check_exists(cls, gallery: str, image_id: int) -> bool:
        """
        说明：
            检查记录是否存在
        参数：
            :param gallery: 图库名
            :param image_id: 图片id
        返回：
            :returns: 若记录存在，返回True
        """
        query = await cls.query.where(
            (cls.gallery == gallery) & (cls.image_id == image_id)
        ).gino.first()
        if query:
            return True
        return False

    @classmethod
    async def get_record(cls, gallery: str, image_id: int) -> Optional["ImageUpload"]:
        """
        说明：
            获取记录
        参数：
            :param gallery: 图库名
            :param image_id: 图片id
        返回：
            :returns: 若记录存在，返回True
        """
        query = await cls.query.where(
            (cls.gallery == gallery) & (cls.image_id == image_id)
        ).gino.first()
        if query:
            return query
        return None

    @classmethod
    async def update_record(
        cls,
        record:"ImageUpload",
        gallery: Optional[str] = None,
        image_id: Optional[int] = None,
        is_record: Optional[bool] = None
    ):
        """
        说明：
            更新记录
        参数：
            :param record: 原来的记录
            :param gallery: 新图库名
            :param image_id: 新图片id
            :param is_record: 是否已记录
        """
        await record.update(
            gallery=gallery or record.gallery,
            image_id=image_id or record.image_id,
            is_record=is_record or record.is_record
        ).apply()

    @classmethod
    async def check_record(cls, gallery: str, image_id: int):
        """
        说明：
            检查图片是否已记录
        参数：
            :param gallery: 图库名
            :param image_id: 图片id
            :param
        """
        query = await cls.query.where(
            (cls.gallery == gallery) & (cls.image_id == image_id)
        ).gino.first()
        if query and query.is_record:
            return True
        return False
