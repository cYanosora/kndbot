import difflib
from typing import List,Union, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from configs.path_config import FONT_PATH
try:
    import ujson as json
except:
    import json


# 时间戳格式化
def timeremain(time):
    if time < 60:
        return f'{int(time)}秒'
    elif time < 60*60:
        return f'{int(time / 60)}分{int(time % 60)}秒'
    elif time < 60*60*24:
        hours = int(time / 60 / 60)
        remain = time - 3600 * hours
        return f'{int(time / 60 / 60)}小时{int(remain / 60)}分{int(remain % 60)}秒'
    else:
        days = int(time / 3600 / 24)
        remain = time - 3600 * 24 * days
        return f'{int(days)}天{timeremain(remain)}'


# 获取字符串相似度
def string_similar(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).quick_ratio()


# 文字生成图片
def t2i(
    text: str,
    font_size: int = 40,
    font_color: str = "black",
    padding: Optional[Tuple[int, int, int, int]] = (0, 0, 0, 0),
    max_width: Optional[int] = None,
    wrap_type: str = "left",
    line_interval: Optional[int] = None,
) -> Image:
    """
    根据文字生成图片，仅使用思源字体，支持\n换行符的输入
    :param text: 文字内容
    :param font_size: 文字大小
    :param font_color: 文字颜色
    :param padding: 文字边距，参数顺序为上下左右
    :param max_width: 限制的文字宽度，文字超出此宽度自动换行
    :param wrap_type: 换行后文字的对齐方式（左对齐left，居中对齐center，右对齐right）
    :param line_interval: 文字有多行时的行间距，默认为字体大小的1/4
    """
    # 仿照meetwq佬的PIL工具插件imageutils的text2image方法制作的简易版
    # 工具地址(https://github.com/noneplugin/nonebot-plugin-imageutils)
    if wrap_type not in ['left', 'center', 'right']:
        raise TypeError('对齐方式参数错误！')
    lines = text.split('\n')
    if max_width is not None:
        def wrap(line, max_width):
            font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), font_size)
            (_w, _), (_, _) = font.font.getsize(line)
            last_idx = 0
            for idx in range(len(line)):
                (_tmp_w, _), (_, _) = font.font.getsize(line[last_idx: idx+1])
                if _tmp_w > max_width:
                    yield line[last_idx:idx]
                    last_idx = idx
            yield line[last_idx:]
        new_lines = []
        for line in lines:
            l = wrap(line, max_width)
            new_lines.extend(l)
        lines = new_lines
    imgs = []
    width = 0
    height = 0
    line_interval = line_interval if line_interval is not None else font_size//4
    for line in lines:
        font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), font_size)
        (_width, _height), (offset_x, offset_y) = font.font.getsize(line)
        img = Image.new('RGBA', (_width, _height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.text((-offset_x + padding[2], -offset_y + padding[0]), line, font_color, font)
        width = _width if width < _width else width
        height += _height + line_interval
        imgs.append(img)
    height -= line_interval
    size = (width + padding[2] + padding[3], height + padding[0] + padding[1])
    pic = Image.new('RGBA', size, (255, 255, 255, 0))
    _h = 0
    for img in imgs:
        if wrap_type == 'left':
            _w = 0
        elif wrap_type == 'center':
            _w = (width - img.width) // 2
        else:
            _w = width - img.width
        pic.paste(img, (_w, _h), mask=img.split()[-1])
        _h += line_interval + img.height
    return pic


# 组合PIL图片
def union(
    img_ls: List['Image'],
    length: int = 0,
    interval: int = 0,
    interval_size: int = 0,
    interval_color: Union[str,Tuple] = 'black',
    padding: Tuple[int, int, int, int] = (0, 0, 0, 0),
    border_size: int = 0,
    border_color: Union[str,Tuple] = 'black',
    border_type: str = 'rectangle',
    border_radius: int = 0,
    type: str = 'col',
    align_type: str = 'center',
    bk_color: Optional[Union[str,Tuple]] = None,
) -> Image:
    """
    组合图片
    :param img_ls: 需要组合的图片列表
    :param length: 组合方向规定的宽度，当length过小时自动使用interval作为图片间隔
    :param interval: 组合方向规定的间隔，当interval为0时按指定的length采用均等间隔
    :param interval_size: 间隔线大小
    :param interval_color: 间隔线颜色
    :param padding: 组合后图片的padding大小，参数顺序为上下左右
    :param border_size: 边框大小
    :param border_color: 边框颜色
    :param border_type: 边框类型，参数为方形"rectangle"或圆角"circle"
    :param border_radius: 当边框类型为"circle"时，指定radius，否则自动使用默认值
    :param type: 组合类型，col为列向组合， row为行向组合
    :param align_type: 非组合方向的对齐类型，left/top为左(上)对齐，center为居中对齐，right/bottom为右(下)对齐
    :param bk_color: 图片背景色， none时背景为透明
    """
    if len(img_ls) == 1:
        return img_ls[0]
    if type not in ['col', 'row']:
        raise TypeError("type类型错误")
    if align_type not in ['top', 'left', 'center', 'right', 'bottom']:
        raise TypeError("align_type类型错误")
    if type == 'col':
        width = length + (len(img_ls) - 1) * interval_size
        height = max([i.height for i in img_ls])
        _sum = sum([i.width for i in img_ls])
        _compare = _sum + interval * (len(img_ls) - 1)
        attr = 'height'
        space = (width - _sum) // (len(img_ls) - 1)
        if space < 0:
            width = _compare
            space = interval
        elif interval > 0 and width >_compare:
            space = interval
    else:
        width = max([i.width for i in img_ls])
        height = length + (len(img_ls) - 1) * interval_size
        _sum = sum([i.height for i in img_ls])
        _compare = _sum + interval * (len(img_ls) - 1)
        attr = 'width'
        space = (height - _sum) // (len(img_ls) - 1)
        if space < 0:
            space = interval
            height = _compare
        elif interval > 0 and height > _compare:
            space = interval
    for i in range(len(img_ls)):
        if img_ls[i].mode != "RGBA":
            img_ls[i] = img_ls[i].convert("RGBA")
    if not bk_color:
        bk_color = (255, 255, 255, 0)
    padding = tuple(i + border_size for i in padding)
    pic = Image.new(
        "RGBA",
        (
            width + padding[2] + padding[3],
            height + padding[0] + padding[1]
        )
    )
    draw = ImageDraw.Draw(pic)
    if border_type == "circle":
        r = border_radius if border_radius else int(min(pic.width, pic.height) / 36)
        draw.rounded_rectangle(
            (0, 0, pic.width, pic.height),
            r,
            bk_color,
            border_color,
            border_size
        )
    elif border_type == "rectangle":
        draw.rectangle(
            (0, 0, pic.width, pic.height),
            bk_color,
            border_color,
            border_size
        )
    else:
        raise TypeError("border_type类型错误")

    _w = 0
    _size = height if attr == 'height' else width
    for idx, img in enumerate(img_ls):
        if align_type in ['top', 'left']:
            _h = 0
        elif align_type == 'center':
            _h = (_size - img.__getattribute__(attr)) // 2
        else:
            _h = _size - img.__getattribute__(attr)
        r, g, b, mask = img.split()
        if attr == 'height':
            pic.paste(img, (_w+padding[2], _h+padding[0]), mask)
            _w += space + img.width
            if interval_size > 0 and idx != len(img_ls) - 1:
                draw = ImageDraw.Draw(pic)
                pos = (_w + padding[2] - space // 2, padding[0], _w + padding[2] - space // 2, pic.height-padding[1])
                draw.line(pos, fill=interval_color, width=interval_size)
        else:
            pic.paste(img, (_h+padding[2], _w+padding[0]), mask)
            _w += space + img.height
            if interval_size > 0 and idx != len(img_ls) - 1:
                draw = ImageDraw.Draw(pic)
                pos = (padding[2], _w + padding[0] - space // 2, pic.width-padding[3], _w + padding[0] - space // 2)
                draw.line(pos, fill=interval_color, width=interval_size)

    return pic

