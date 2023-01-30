import difflib
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from configs.path_config import FONT_PATH
from utils.imageutils import union
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


