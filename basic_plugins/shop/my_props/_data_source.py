from typing import Dict, Optional, List
from PIL import Image
from configs.path_config import IMAGE_PATH
from models.goods_info import GoodsInfo
from utils.imageutils import BuildImage, union

icon_path = IMAGE_PATH / 'shop' / 'icon'


async def create_bag_image(props: Dict[str, int]):
    """
    说明:
        创建背包道具图片
    参数:
        :param props: 道具仓库字典
    """
    goods_list = await GoodsInfo.get_all_goods()
    active_props = await _init_prop(props, [x for x in goods_list if not x.is_passive])
    passive_props = await _init_prop(props, [x for x in goods_list if x.is_passive])
    active_w = active_h = passive_w = passive_h = 0
    # 用户没有任何道具
    if not active_props and not active_props:
        return None
    pad = (80, 60)
    if active_props:
        img = BuildImage.new("RGBA", (active_props.width, active_props.height + 70))
        img.paste(active_props, (0, 70))
        img.draw_text((pad[0], 0,pad[0]*2+400,70), "↓主动道具↓", fill='#4d4d4d',fontsize=40, fontname="SourceHanSansCN-Medium.otf")
        active_props = img
        active_w = img.width
        active_h = img.height
    if passive_props:
        img = BuildImage.new("RGBA", (passive_props.width, passive_props.height + 70))
        img.paste(passive_props, (0, 70))
        img.draw_text((pad[0], 0,pad[0]*2+400,70), "↓被动道具↓", fill='#4d4d4d', fontsize=40, fontname="SourceHanSansCN-Medium.otf")
        passive_props = img
        passive_w = img.width
        passive_h = img.height
    finalpic = BuildImage.open(IMAGE_PATH/'shop'/'background.jpg')
    finalpic = finalpic.resize((max(active_w, passive_w) + pad[0]*2, active_h+passive_h + pad[1]*2))
    curr_w, curr_h = pad
    if active_props:
        finalpic.paste(active_props, (curr_w, curr_h), True)
        curr_h += active_props.height + 10
    if passive_props:
        finalpic.paste(passive_props, (curr_w, curr_h), True)
    return finalpic.pic2bs4()


async def _init_prop(
    props: Dict[str, int], _props: List[GoodsInfo]
) -> Optional['Image']:
    """
    说明:
        构造道具列表图片
    参数:
        :param props: 道具仓库字典
        :param _props: 道具列表
    """
    # left
    prop_border_color = '#555577'
    prop_content_color = '#ddeeee'
    bottom_color = '#5588cc'
    # right
    des_border_color = '#777777'
    content_color = '#e0eaf2'
    tag_color = '#8899aa'
    # union
    text_color = '#555577'
    bk_color = '#eeeeff'
    # 只取在商店有记录的所有道具
    items = [(x, props[x.goods_name]) if x.goods_name in props.keys() else (x, 0) for x in _props]
    image_list = []
    border = 4
    act_id = 0
    pass_id = 0
    for item in items:
        # 跳过用户未拥有的道具
        if item[1] == 0:
            continue
        # 道具介绍图
        itemImg = BuildImage.new('RGBA', (400, 330),prop_content_color)
        itemImg.draw_rectangle((0,0,itemImg.width,85),prop_border_color)
        itemImg.draw_rectangle((0,270,itemImg.width,itemImg.height),bottom_color)
        itemImg.draw_rounded_rectangle((0,0,itemImg.width,itemImg.height),20,None,prop_border_color,border)
        itemImg = itemImg.circle_corner(20)
        # 道具图标
        if icon := item[0].icon:
            iconImg = BuildImage.open(icon_path / icon).resize((128, 128))
            itemImg.paste(iconImg, (132, 105))
        # 道具id
        if item[0].is_passive:
            pass_id += 1
        else:
            act_id += 1
        itemImg.draw_text(
            (0,0,60,85),str(act_id if not item[0].is_passive else pass_id), fill='white',
            fontname="SourceHanSansCN-Medium.otf", max_fontsize=30, valign='center',halign='center'
        )
        # 道具名称
        itemImg.draw_text(
            (0,0,itemImg.width,85),item[0].goods_name, fill='white',
            fontname="SourceHanSansCN-Medium.otf", max_fontsize=30, valign='center',halign='center'
        )
        # 道具持有数
        itemImg.draw_text((20, 270), '持有数', fontsize=36,fontname="SourceHanSansCN-Medium.otf",fill='white')
        itemImg.draw_text(
            (330, 270, itemImg.width, itemImg.height), str(item[1]),fill='white',
            fontsize=36,fontname="SourceHanSansCN-Medium.otf", valign='center',halign='center'
        )
        # 道具简介
        itemDesImg = BuildImage.new('RGBA', (900, 330))
        _tmp1 = BuildImage.new('RGBA', (900, 160))
        _tmp1.draw_rounded_rectangle((0,0,_tmp1.width,_tmp1.height),20,content_color,des_border_color,border)
        _tmp1.draw_rounded_rectangle((30,50,200,110),30,tag_color)
        _tmp2 = _tmp1.copy()
        _tmp1.draw_text((30,50,200,110),'简介',fontsize=25,fill='white',fontname="SourceHanSansCN-Medium.otf", valign='center',halign='center')
        _tmp2.draw_text((30,50,200,110),'效果',fontsize=25,fill='white',fontname="SourceHanSansCN-Medium.otf", valign='center',halign='center')
        _tmp1.draw_text_raw(
            (230,10,_tmp1.width-30,_tmp1.height-10), item[0].goods_description,fill=text_color,
            fontsize=30, fontname="SourceHanSansCN-Medium.otf",halign='center', valign='center'
        )
        _tmp2.draw_text_raw(
            (230,10,_tmp2.width-30,_tmp2.height-10), item[0].goods_effect,fill=text_color,
            fontsize=30, fontname="SourceHanSansCN-Medium.otf",halign='center', valign='center'
        )
        itemDesImg.paste(_tmp1,(0,0),True)
        itemDesImg.paste(_tmp2,(0,170),True)
        image_list.append(union([itemImg.image, itemDesImg.image], type='col', interval=10))
    # 不存在道具，返回空值
    if len(image_list) == 0:
        return None
    final_image = union(
        image_list, type='row', interval=15, padding=(30, 30, 30, 30),
        border_type='circle', border_radius=20, bk_color=bk_color
    )
    return final_image
