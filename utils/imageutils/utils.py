from configs.path_config import IMAGE_PATH
from PIL import Image, ImageFile, ImageDraw
from imagehash import ImageHash
from io import BytesIO
from matplotlib import pyplot as plt
from typing import Union, Tuple, List, Optional
from pathlib import Path
import cv2
import base64
import imagehash
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


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
    if type not in ['col', 'row']:
        raise TypeError("type类型错误")
    if align_type not in ['top', 'left', 'center', 'right', 'bottom']:
        raise TypeError("align_type类型错误")
    img_len_sub1 = len(img_ls) - 1 if len(img_ls) > 1 else 1
    if type == 'col':
        width = length + img_len_sub1 * interval_size
        height = max([i.height for i in img_ls])
        _sum = sum([i.width for i in img_ls])
        _compare = _sum + interval * img_len_sub1
        attr = 'height'
        space = (width - _sum) // img_len_sub1
        if space < 0:
            width = _compare
            space = interval
        elif interval > 0 and width >_compare:
            space = interval
    else:
        width = max([i.width for i in img_ls])
        height = length + img_len_sub1 * interval_size
        _sum = sum([i.height for i in img_ls])
        _compare = _sum + interval * img_len_sub1
        attr = 'width'
        space = (height - _sum) // img_len_sub1
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

def compare_image_with_hash(
    image_file1: str, image_file2: str, max_dif: int = 1.5
) -> bool:
    """
    说明：
        比较两张图片的hash值是否相同
    参数：
        :param image_file1: 图片文件路径
        :param image_file2: 图片文件路径
        :param max_dif: 允许最大hash差值, 越小越精确,最小为0
    """
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    hash_1 = get_img_hash(image_file1)
    hash_2 = get_img_hash(image_file2)
    dif = hash_1 - hash_2
    if dif < 0:
        dif = -dif
    if dif <= max_dif:
        return True
    else:
        return False


def get_img_hash(image_file: Union[str, Path]) -> ImageHash:
    """
    说明：
        获取图片的hash值
    参数：
        :param image_file: 图片文件路径
    """
    with open(image_file, "rb") as fp:
        hash_value = imagehash.average_hash(Image.open(fp))
    return hash_value


def compressed_image(
    in_file: Union[str, Path], out_file: Union[str, Path] = None, ratio: float = 0.9
):
    """
    说明：
        压缩图片
    参数：
        :param in_file: 被压缩的文件路径
        :param out_file: 压缩后输出的文件路径
        :param ratio: 压缩率，宽高 * 压缩率
    """
    in_file = IMAGE_PATH / in_file if isinstance(in_file, str) else in_file
    if out_file:
        out_file = (
            IMAGE_PATH / out_file if isinstance(out_file, str) else out_file
        )
    else:
        out_file = in_file
    h, w, d = cv2.imread(str(in_file.absolute())).shape
    img = cv2.resize(
        cv2.imread(str(in_file.absolute())), (int(w * ratio), int(h * ratio))
    )
    cv2.imwrite(str(out_file.absolute()), img)


def alpha2white_pil(pic: Image) -> Image:
    """
    说明：
        将图片透明背景转化为白色
    参数：
        :param pic: 通过PIL打开的图片文件
    """
    img = pic.convert("RGBA")
    width, height = img.size
    for yh in range(height):
        for xw in range(width):
            dot = (xw, yh)
            color_d = img.getpixel(dot)
            if color_d[3] == 0:
                color_d = (255, 255, 255, 255)
                img.putpixel(dot, color_d)
    return img


def pic2b64(pic: Image) -> str:
    """
    说明：
        PIL图片转base64
    参数：
        :param pic: 通过PIL打开的图片文件
    """
    buf = BytesIO()
    pic.save(buf, format="PNG")
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return "base64://" + base64_str


def fig2b64(plt_: plt) -> str:
    """
    说明：
        matplotlib图片转base64
    参数：
        :param plt_: matplotlib生成的图片
    """
    buf = BytesIO()
    plt_.savefig(buf, format="PNG", dpi=100)
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return "base64://" + base64_str


def is_valid(file: str) -> bool:
    """
    说明：
        判断图片是否损坏
    参数：
        :param file: 图片文件路径
    """
    valid = True
    try:
        Image.open(file).load()
    except OSError:
        valid = False
    return valid
