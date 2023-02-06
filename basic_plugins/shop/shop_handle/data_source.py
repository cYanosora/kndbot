import datetime
import math
import os
import time
import random
from typing import Optional, Union, Tuple, List
from PIL import Image
from models.goods_info import GoodsInfo
from utils.utils import is_number
from utils.imageutils import BuildImage as IMG, union
from configs.path_config import IMAGE_PATH


icon_path = IMAGE_PATH / 'shop' / 'icon'
# GDict['run_sql'].append("ALTER TABLE goods_info ADD COLUMN goods_effect TEXT default '' NOT NULL;")
# GDict['run_sql'].append("ALTER TABLE goods_info ADD COLUMN daily_limit integer DEFAULT 0 NOT NULL;")
# GDict['run_sql'].append("ALTER TABLE goods_info ADD COLUMN daily_purchase_limit json DEFAULT '{}' NOT NULL;")
# GDict['run_sql'].append("ALTER TABLE goods_info ADD COLUMN is_passive boolean DEFAULT False NOT NULL;")
# GDict['run_sql'].append("ALTER TABLE goods_info ADD COLUMN icon VARCHAR(255);")
# GDict['run_sql'].append("ALTER TABLE goods_info ADD COLUMN is_show boolean DEFAULT True NOT NULL;")


async def _init_goods(goods: List[GoodsInfo], limit_height: int) -> Optional['Image']:
    fontname = "SourceHanSansCN-Regular.otf"
    image_list = []
    good_left_size = (250, 210)
    good_right_size = (600, 210)
    border = 4
    # left
    good_border_color = '#4d4d4d'
    good_content_color = '#ddeeee'
    time_color = '#bbaaee'
    bottom_color = '#5588cc'
    # right
    des_border_color = '#777777'
    content_color = '#e0eaf2'
    tag_color = '#8899aa'
    # union
    text_color = '#555577'
    bk_color = '#eeeeff'
    goods_num = 0
    for good in goods:
        # 若商品已下架
        if good.goods_limit_time != 0 and time.time() > good.goods_limit_time:
            continue
        # 若商品不展示
        if not good.is_show:
            continue
        goods_num += 1
        good_left = IMG.new('RGBA',good_left_size, good_content_color)
        good_left.draw_rectangle((0,175,good_left.width, good_left.height),bottom_color)
        # 商品id
        good_left.draw_rounded_rectangle((-20,-20,50,50),20,good_border_color)
        good_left.draw_text((0,0,50,50),str(goods_num),fill='white',fontsize=25,valign='center',halign='center',fontname=fontname)
        # 商品限时、名称
        if good.goods_limit_time > time.time():
            icon_offset = 0
            good_left.draw_rectangle((0,150,good_left.width,175), time_color)
            end_time = datetime.datetime.fromtimestamp(good.goods_limit_time)
            limit_time = datetime.datetime.strftime(end_time, '%m/%d %H:%M') + "下架"
            good_left.draw_text_raw(
                (0,120,good_left.width,145),good.goods_name,
                fontname=fontname, fill=good_border_color,fontsize=20,halign='center',valign='center'
            )
            good_left.draw_text_raw(
                (0,145,good_left.width,170),limit_time,halign='center',valign='center',
                fontname=fontname, fontsize=20, fill='white'
            )
        else:
            icon_offset = 15
            good_left.draw_text_raw(
                (0,145,good_left.width,170),good.goods_name,halign='center',valign='center',
                fontname=fontname, fontsize=20, fill=good_border_color
            )
        good_left = good_left.circle_corner(20)
        good_left.draw_rounded_rectangle((0, 0, good_left.width, good_left.height), 20, None, good_border_color, border)
        # 商品图标
        if good.icon:
            icon = IMG.open(icon_path / good.icon).resize((72,72))
            good_left.paste(icon,(89,28+icon_offset),True)
        # 商品价格
        if good.goods_price < 0:
            good_left.draw_text_raw(
                (75, 173), str("无法售出"), fontsize=24, fontname=fontname, fill=good_border_color
            )
        else:
            if good.goods_discount < 1:
                discount = f"优惠{100-int(good.goods_discount * 100)}%"
                good_left.draw_text_raw(
                    (10,175),discount,fontsize=20,fontname=fontname, fill='white'
                )
                good_left.paste(IMG.open(IMAGE_PATH/'shop'/'coin.png').resize((40, 40)),(100, 173), True)
                good_left.draw_text_raw(
                    (140,173),str(good.goods_price),fontsize=24,fontname=fontname, fill='white'
                )
                good_left.draw_line((135,190,135+len(str(good.goods_price))*18,190), fill='red',width=2)
                good_left.draw_text_raw(
                    (200,173),str(math.ceil(good.goods_price*good.goods_discount)),fontsize=24,fontname=fontname, fill='white'
                )
            else:
                good_left.paste(IMG.open(IMAGE_PATH/'shop'/'coin.png').resize((40, 40)),(100, 173), True)
                good_left.draw_text_raw(
                    (140,173),str(good.goods_price),fontsize=24,fontname=fontname, fill='white'
                )
        # 商品简介图
        good_right = IMG.new('RGBA', good_right_size)
        _tmp1 = IMG.new('RGBA', (600, 100))
        _tmp1.draw_rounded_rectangle((0,0,_tmp1.width,_tmp1.height),20,content_color,des_border_color,border)
        _tmp1.draw_rounded_rectangle((20,30,110,70),20,tag_color)
        _tmp2 = _tmp1.copy()
        _tmp1.draw_text((20,30,110,70),'简介',fontsize=20,fill='white',fontname="SourceHanSansCN-Medium.otf", valign='center',halign='center')
        _tmp2.draw_text((20,30,110,70),'效果',fontsize=20,fill='white',fontname="SourceHanSansCN-Medium.otf", valign='center',halign='center')
        _tmp1.draw_text_raw(
            (130,0,_tmp1.width-20,_tmp1.height), good.goods_description,fill=text_color,
            fontsize=24, fontname="SourceHanSansCN-Medium.otf",halign='center',valign='center',
        )
        _tmp2.draw_text_raw(
            (130,0,_tmp2.width-20,_tmp2.height), good.goods_effect,fill=text_color,
            fontsize=24, fontname="SourceHanSansCN-Medium.otf",halign='center',valign='center',
        )
        good_right.paste(_tmp1,(0,0),True)
        good_right.paste(_tmp2,(0,105),True)
        goodpic = union([good_left.image, good_right.image], type='col', interval=10)
        image_list.append(goodpic)
    # 无商品返回空值
    if len(image_list) == 0:
        return None
    columns = round(sum(i.height for i in image_list) / limit_height)
    picnum = math.ceil(len(image_list) / columns)
    union_image = union(
        image_list[:picnum], type='row', interval=10, bk_color=bk_color,
        padding=(20,20,15,15), border_type='circle'
    )
    for c in range(columns - 1):
        _ = union(
            image_list[picnum * (c + 1):picnum * (c + 2)], type='row', interval=10,
            bk_color=bk_color, padding=(20,20,15,15), border_type='circle'
        )
        union_image = union([union_image, _], type='col', interval=15, align_type='top')
    return union_image


async def create_shop_help() -> str:
    """
    制作商店图片
    :return: 图片base64
    """
    # 商店像素小人
    shop_chara = IMG.open(IMAGE_PATH / "shop" / "title.png").resize((150, 150))
    # 商店字样贴图
    shop_logo = IMG.open(IMAGE_PATH / "shop" / "text.png").resize((80, 100))
    # 商店卡通小人
    shop_corner = IMG.open(IMAGE_PATH / "shop" / "corner.png").resize((150, 180))
    # 商店看板娘贴图
    rdint = len([i for i in os.listdir(IMAGE_PATH / "shop") if i.startswith("shop")])
    knd_img = IMG.open(IMAGE_PATH / "shop" / f"shop{random.randint(0, rdint - 1)}.png")
    # 商店背景
    basebk = IMG.open(IMAGE_PATH / "shop" / "background.jpg")
    # basebk.filter("GaussianBlur", 10)
    # 商店道具
    goods_lst = await GoodsInfo.get_all_goods()
    goods_img = await _init_goods(goods_lst, knd_img.height)
    # 合成商店图片
    shop_pad = (30, 20)
    w = goods_img.width + shop_pad[0] * 2 + 400
    h = goods_img.height + shop_pad[1] * 2 + 200
    fontname = "SourceHanSansCN-Regular.otf"
    # 商店界面
    shop = IMG.new("RGBA", (w, h))
    # 粘贴商店背景
    shop.paste(basebk.resize(shop.size), alpha=True)
    # 粘贴商店道具
    shop.paste(goods_img, (shop_pad[0], shop_pad[1] + 200), True)
    # 粘贴商店看板娘
    shop.paste(knd_img, (goods_img.width+20, shop.height-knd_img.height), True)
    # 粘贴商店字样
    shop.paste(shop_logo, (180, 50), True)
    # 粘贴商店像素小人
    shop.paste(shop_chara, (0, 0), True)
    # 粘贴商店卡通小人
    shop.paste(shop_corner, (goods_img.width-580, 0), True)
    # 粘贴商店说明
    shop.draw_text(
        (360, 30, 980, 60),
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
        (goods_img.width-400, 50),
        "奏宝本人    售价：2525252525金币\n"
        "    如果攒够买奏宝的钱会怎么样（",
        fontsize=25,
        fontname=fontname,
        fill=(68, 68, 102),
        ischeckchar=False
    )
    return shop.pic2bs4()


# 添加商品进数据库
async def register_goods(
    name: str,
    price: int,
    des: str,
    effect: str,
    discount: Optional[float] = 1,
    limit_time: Optional[int] = 0,
    daily_limit: Optional[int] = 0,
    is_passive: Optional[bool] = False,
    is_show: Optional[bool] = True,
    icon: Optional[str] = None,
) -> bool:
    """
    添加商品
    例如：                                                  折扣：可选参数↓  限时时间:可选，单位为小时
        添加商品 name:萝莉酒杯 price:9999 des:普通的酒杯，但是里面.. discount:0.4 limit_time:90
        添加商品 name:可疑的药 price:5 des:效果未知
    参数：
        :param name: 商品名称
        :param price: 商品价格
        :param des: 商品简介
        :param effect: 商品效果
        :param discount: 商品折扣
        :param limit_time: 商品限时销售时间，单位为小时
        :param daily_limit: 每日购买次数限制
        :param is_passive: 是否为被动
        :param is_show: 道具是否展示在商店内
        :param icon: 图标
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
            name, int(price), des, effect, float(discount),
            limit_time, daily_limit, is_passive, is_show, icon
        )
    return False


# 从数据库中删除商品
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


# 更新商品信息
async def update_goods(**kwargs) -> Tuple[bool, str, str]:
    """
    更新商品信息
    :param kwargs: kwargs
    :return: 更新状况
    """
    if kwargs:
        goods_lst = await GoodsInfo.get_all_goods()
        if is_number(kwargs["name"]):
            if int(kwargs["name"]) < 1 or int(kwargs["name"]) > len(goods_lst):
                return False, "序号错误，没有该序号的商品...", ""
            goods = goods_lst[int(kwargs["name"]) - 1]
        else:
            goods = await GoodsInfo.get_goods_info(kwargs["name"])
            if not goods:
                return False, "名称错误，没有该名称的商品...", ""
        name: str = goods.goods_name
        price = goods.goods_price
        des = goods.goods_description
        effect = goods.goods_effect
        discount = goods.goods_discount
        limit_time = goods.goods_limit_time
        daily_limit = goods.daily_limit
        is_passive = goods.is_passive
        is_show = goods.is_show
        icon = goods.icon
        new_time = 0
        tmp = ""
        if kwargs.get("price"):
            tmp += f'价格：{price} --> {kwargs["price"]}\n'
            price = kwargs["price"]
        if kwargs.get("des"):
            tmp += f'描述：{des} --> {kwargs["des"]}\n'
            des = kwargs["des"]
        if kwargs.get("effect"):
            tmp += f'效果：{effect} --> {kwargs["effect"]}\n'
            des = kwargs["effect"]
        if kwargs.get("discount"):
            tmp += f'折扣：{discount} --> {kwargs["discount"]}\n'
            discount = kwargs["discount"]
        if kwargs.get("limit_time"):
            kwargs["limit_time"] = float(kwargs["limit_time"])
            new_time = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(time.time() + kwargs["limit_time"] * 60 * 60),
            ) if kwargs["limit_time"] != 0 else 0
            tmp += f"限时至： {new_time}\n" if new_time else "取消了限时\n"
            limit_time = kwargs["limit_time"]
        if kwargs.get("daily_limit"):
            tmp += f'每日购买限制：{daily_limit} --> {kwargs["daily_limit"]}\n' if daily_limit else "取消了购买限制\n"
            daily_limit = int(kwargs["daily_limit"])
        if kwargs.get("is_passive"):
            tmp += f'被动道具：{is_passive} --> {kwargs["is_passive"]}\n'
            is_passive = kwargs["is_passive"]
        if kwargs.get("is_show"):
            tmp += f'是否展示于商店：{is_show} --> {kwargs["is_show"]}\n'
            is_show = kwargs["is_show"]
        if kwargs.get("icon"):
            tmp += f'道具图标文件名：{is_show} --> {kwargs["icon"]}\n'
            icon = kwargs["icon"]
        await GoodsInfo.update_goods(
            name,
            int(price),
            des,
            effect,
            float(discount),
            int(
                time.time() + limit_time * 60 * 60
                if limit_time != 0 and new_time
                else 0
            ),
            daily_limit,
            is_passive,
            is_show,
            icon
        )
        return True, name, tmp[:-1],


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
                if not sp[1].isdigit():
                    return "price参数不合法，必须为整数，负数时认定为无法售出！"
                data["price"] = sp[1]
            elif sp[0] == "des":
                data["des"] = sp[1]
            elif sp[0] == 'effect':
                data["effect"] = sp[1]
            elif sp[0] == "discount":
                if not is_number(sp[1]) or float(sp[1]) < 0:
                    return "discount参数不合法，必须大于0！"
                data["discount"] = sp[1]
            elif sp[0] == "limit_time":
                if not is_number(sp[1]) or float(sp[1]) < 0:
                    return "limit_time参数不合法，必须为数字且大于0！"
                data["limit_time"] = sp[1]
            elif sp[0] == "daily_limit":
                if not is_number(sp[1]) or float(sp[1]) < 0:
                    return "daily_limit参数不合法，必须为数字且大于0！"
                data["daily_limit"] = sp[1]
            elif sp[0] == "is_passive":
                data["is_passive"] = True if sp[1].lower() == 'true' else False
            elif sp[0] == "is_show":
                data["is_show"] = True if sp[1].lower() == 'true' else False
            elif sp[0] == "icon":
                data["icon"] = sp[1]
    return data
