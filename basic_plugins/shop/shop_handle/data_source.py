import os
import time
import random
from typing import Optional, Union
from models.goods_info import GoodsInfo
from utils.imageutils import BuildImage as IMG, Text2Image
from utils.utils import is_number
from configs.path_config import IMAGE_PATH


async def create_shop_help() -> str:
    """
    制作商店图片
    :return: 图片base64
    """
    goods_lst = await GoodsInfo.get_all_goods()
    fontname = "SourceHanSansCN-Regular.otf"
    _dc = {}
    _list = []
    # 得到商店界面大小
    h = 0
    for goods in goods_lst:
        if goods.goods_limit_time == 0 or time.time() < goods.goods_limit_time:
            h += len(goods.goods_description.strip().split("\n")) * 90
            _list.append(goods)
    h -= 10
    # 生成最终的商店界面
    w = 1000    # 商店宽度
    h = h + 230 + 100
    h = 1000 if h < 1000 else h     # 商店高度
    # 商店像素小人
    shop_chara = IMG.open(IMAGE_PATH / "shop" / "title.png").resize((150, 150))
    # 商店字样贴图
    shop_logo = IMG.open(IMAGE_PATH / "shop" / "text.png").resize((80, 100))
    # 商店卡通小人
    shop_corner = IMG.open(IMAGE_PATH / "shop" / "corner.png").resize((150, 180))
    # 商店界面
    shop = IMG.new("RGBA", (w, h), "#f9f6f2")
    # 商店背景
    basebk = IMG.open(IMAGE_PATH / "shop" / "background.jpg").resize((w, h))
    basebk.filter("GaussianBlur", 10)
    # 粘贴商店背景
    shop.paste(basebk, alpha=True)
    rdint = len([i for i in os.listdir(IMAGE_PATH / "shop") if i.startswith("shop")])
    # 商店看板娘贴图
    knd_img = IMG.open(IMAGE_PATH / "shop" / f"shop{random.randint(0, rdint-1)}.png")
    # 粘贴商店看板娘
    shop.paste(knd_img, (520, 230), True)
    # 粘贴商店字样
    shop.paste(shop_logo, (180, 50), True)
    # 粘贴商店像素小人
    shop.paste(shop_chara, (0, 0), True)
    # 粘贴商店卡通小人
    shop.paste(shop_corner, (20, h-200), True)
    # shop.paste(A, (30, 220))
    # 粘贴商店说明
    shop.draw_text(
        (360, 20, 980, 50),
        "请通过 '序号' 或者 '商品名称' 购买 。例如：购买 杯面 3\n"
        "购买后如何使用道具？ 例如：使用道具 1\n"
        "自己持有的道具序号请通过 '我的道具' 获取\n"
        "前三个道具会在无签到加成道具时自动使用，其它道具需要手动使用。",
        fontsize=20,
        halign="center",
        fontname=fontname,
        fill=(252, 95, 174),
        ischeckchar=False
    )
    shop.draw_text(
        (180, h - 100),
        "奏宝本人    售价：2525252525金币\n"
        "    如果攒够买奏宝的钱会怎么样（",
        fontsize=24,
        fontname=fontname,
        fill=(68, 68, 102),
        ischeckchar=False
    )
    # 最后粘贴商店道具
    idx = 1
    current_h = 0
    for goods in _list:
        # fontsize20
        goods_image = IMG.new(
            "RGBA",
            (580, 80),
            color=(255, 255, 255, 0)
        )
        #font_size25
        name_image = IMG.new(
            "RGBA",
            (580, 40),
            color="#E0EAF2"
        )
        #font_size=25
        des_image = IMG.new(
            "RGBA",
            (580, len(goods.goods_description.strip().split("\n")) * 40),
            color="#5486C3"
        )
        name_image.draw_text(
            (15, 3),
            f"{idx}.{goods.goods_name}",
            fontname=fontname,
            fontsize=25,
            fill=(68, 68, 102),
            ischeckchar=False
        )
        sale_image = Text2Image.from_bbcode_text(
            f"售价：[color=#BB6688]{goods.goods_price}[/color] 金币",
            fontname=fontname,
            fontsize=25
        ).to_image()
        name_image.paste(sale_image, (390, 3), True)
        name_image.draw_rounded_rectangle((0, 0, 580, 40), 15, outline="#4D4D4D", width=4)
        name_image.draw_rounded_rectangle((0, 0, 580, 40), 15, outline="#767578", width=2)
        name_image = name_image.circle_corner(14)
        des_image.draw_rounded_rectangle((0, 0, 580, 40), 15, outline="#4D4D4D", width=4)
        des_image.draw_rounded_rectangle((0, 0, 580, 40), 15, outline="#767578", width=2)
        des_image = des_image.circle_corner(14)

        goods_image.paste(name_image, (0, 0), True)
        goods_image.paste(des_image, (0, 39), True)

        goods_image.draw_text(
            (10, 44),
            f"简介：{goods.goods_description}",
            fontname=fontname,
            fontsize=20,
            fill=(255, 255, 255),
            ischeckchar=False
        )
        shop.paste(goods_image, (30, 220 + current_h), True)
        idx += 1
        current_h += 90
    return shop.pic2bs4()


async def register_goods(
    name: str,
    price: int,
    des: str,
    discount: Optional[float] = 1,
    limit_time: Optional[int] = 0,
) -> bool:
    """
    添加商品
    例如：                                   折扣：可选参数↓  限时时间:可选，单位为小时
        添加商品 name:杯面 price:100 des:家常必备品 discount:0.4 limit_time:90
    :param name: 商品名称
    :param price: 商品价格
    :param des: 商品简介
    :param discount: 商品折扣
    :param limit_time: 商品限时销售时间，单位为小时
    :return: 是否添加成功
    """
    if not await GoodsInfo.get_goods_info(name):
        limit_time = float(limit_time) if limit_time else limit_time
        discount = discount if discount is not None else 1
        limit_time = (
            int(time.time() + limit_time * 60 * 60)
            if limit_time is not None and limit_time != 0
            else 0
        )
        return await GoodsInfo.add_goods(
            name, int(price), des, float(discount), limit_time
        )
    return False


async def delete_goods(name: str, id_: int) -> "str, str, int":
    """
    删除商品
    :param name: 商品名称
    :param id_: 商品id
    :return: 删除状况
    """
    goods_lst = await GoodsInfo.get_all_goods()
    if id_:
        if id_ < 1 or id_ > len(goods_lst):
            return "序号错误，没有该序号商品...", "", 999
        goods_name = goods_lst[id_ - 1].goods_name
        if await GoodsInfo.delete_goods(goods_name):
            return f"删除商品 {goods_name} 成功！", goods_name, 200
        else:
            return f"删除商品 {goods_name} 失败！", goods_name, 999
    if name:
        if await GoodsInfo.delete_goods(name):
            return f"删除商品 {name} 成功！", name, 200
        else:
            return f"删除商品 {name} 失败！", name, 999


async def update_goods(**kwargs) -> "str, str, int":
    """
    更新商品信息
    :param kwargs: kwargs
    :return: 更新状况
    """
    if kwargs:
        goods_lst = await GoodsInfo.get_all_goods()
        if is_number(kwargs["name"]):
            if int(kwargs["name"]) < 1 or int(kwargs["name"]) > len(goods_lst):
                return "序号错误，没有该序号的商品...", "", 999
            goods = goods_lst[int(kwargs["name"]) - 1]
        else:
            goods = await GoodsInfo.get_goods_info(kwargs["name"])
            if not goods:
                return "名称错误，没有该名称的商品...", "", 999
        name = goods.goods_name
        price = goods.goods_price
        des = goods.goods_description
        discount = goods.goods_discount
        limit_time = goods.goods_limit_time
        new_time = 0
        tmp = ""
        if kwargs.get("price"):
            tmp += f'价格：{price} --> {kwargs["price"]}\n'
            price = kwargs["price"]
        if kwargs.get("des"):
            tmp += f'描述：{des} --> {kwargs["des"]}\n'
            des = kwargs["des"]
        if kwargs.get("discount"):
            tmp += f'折扣：{discount} --> {kwargs["discount"]}\n'
            discount = kwargs["discount"]
        if kwargs.get("limit_time"):
            kwargs["limit_time"] = float(kwargs["limit_time"])
            new_time = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(time.time() + kwargs["limit_time"] * 60 * 60),
            )
            tmp += f"限时至： {new_time}\n"
            limit_time = kwargs["limit_time"]
        return (
            await GoodsInfo.update_goods(
                name,
                int(price),
                des,
                float(discount),
                int(
                    time.time() + limit_time * 60 * 60
                    if limit_time != 0 and new_time
                    else 0
                ),
            ),
            name,
            tmp[:-1],
        )


def parse_goods_info(msg: str) -> Union[dict, str]:
    """
    解析格式数据
    :param msg: 消息
    :return: 解析完毕的数据data
    """
    if "name:" not in msg:
        return "必须指定修改的商品名称或序号！"
    data = {}
    for x in msg.split():
        sp = x.split(":", maxsplit=1)
        if str(sp[1]).strip():
            sp[1] = sp[1].strip()
            if sp[0] == "name":
                data["name"] = sp[1]
            elif sp[0] == "price":
                if not is_number(sp[1]) or int(sp[1]) < 0:
                    return "price参数不合法，必须大于等于0！"
                data["price"] = sp[1]
            elif sp[0] == "des":
                data["des"] = sp[1]
            elif sp[0] == "discount":
                if not is_number(sp[1]) or float(sp[1]) < 0:
                    return "discount参数不合法，必须大于0！"
                data["discount"] = sp[1]
            elif sp[0] == "limit_time":
                if not is_number(sp[1]) or float(sp[1]) < 0:
                    return "limit_time参数不合法，必须大于0！"
                data["limit_time"] = sp[1]
    return data
