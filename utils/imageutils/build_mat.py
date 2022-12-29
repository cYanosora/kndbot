from PIL import Image, ImageFile
from .text2image import Text2Image
from .build_image import BuildImage as IMG
from typing import Tuple, Optional, Union, List
from pathlib import Path
from math import ceil
import random
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


class BuildMat:
    """
    针对 折线图/柱状图，基于 BuildImage 编写的 非常难用的 自定义画图工具
    目前仅支持 正整数
    """

    def __init__(
        self,
        y: List[int],
        mat_type: str = "line",
        *,
        x_name: Optional[str] = None,
        y_name: Optional[str] = None,
        x_index: List[Union[str, int, float]] = None,
        y_index: List[Union[str, int, float]] = None,
        x_rotate: int = 0,
        title: Optional[str] = None,
        size: Tuple[int, int] = (2000, 1600),
        font: str = "msyh.ttf",
        font_size: Optional[int] = None,
        display_num: bool = False,
        is_grid: bool = False,
        background: Optional[List[str]] = None,
        background_filler_type: Optional[str] = "center",
        bar_color: Optional[List[Union[str, Tuple[int, int, int]]]] = None,
    ):
        """
        说明：
            初始化 BuildMat
        参数：
            :param y: 坐标值
            :param mat_type: 图像类型 可能的值：[line]: 折线图，[bar]: 柱状图，[barh]: 横向柱状图
            :param x_name: 横坐标名称
            :param y_name: 纵坐标名称
            :param x_index: 横坐标值
            :param y_index: 纵坐标值
            :param x_rotate: 横坐标旋转角度
            :param title: 标题
            :param size: 图像大小，建议默认
            :param font: 字体
            :param font_size: 字体大小，建议默认
            :param display_num: 是否显示数值
            :param is_grid: 是否添加栅格
            :param background: 背景图片
            :param background_filler_type: 图像填充类型
            :param bar_color: 柱状图颜色，位 ['*'] 时替换位彩虹随机色
        """
        self.mat_type = mat_type
        self.markImg = None
        self._check_value(y, y_index)
        self.w = size[0]
        self.h = size[1]
        self.y = y
        self.x_name = x_name
        self.y_name = y_name
        self.x_index = x_index
        self.y_index = y_index
        self.x_rotate = x_rotate
        self.title = title
        self.font = font
        self.display_num = display_num
        self.is_grid = is_grid
        self.background = background
        self.background_filler_type = background_filler_type
        self.bar_color = bar_color if bar_color else [(0, 0, 0)]
        self.size = size
        self.padding_w = 240
        self.padding_h = 60
        self.line_length = 1400
        self._deviation = 1
        self._color = {}
        if not font_size:
            self.font_size = int(25 * (1 - len(x_index) / 100))
        else:
            self.font_size = font_size
        if self.bar_color == ["*"]:
            self.bar_color = [
                "#FF0000",
                "#FF7F00",
                "#FFFF00",
                "#00FF00",
                "#00FFFF",
                "#0000FF",
                "#8B00FF",
            ]
        if not x_index:
            raise ValueError("缺少 x_index [横坐标值]...")
        self._x_interval = int((self.line_length - 70) / len(x_index))
        self._bar_width = int(30 * (1 - (len(x_index) + 10) / 100))
        # 没有 y_index 时自动生成
        if not y_index:
            _y_index = []
            _max_value = int(max(y))
            _max_value = ceil(
                _max_value / eval("1" + "0" * (len(str(_max_value)) - 1))
            ) * eval("1" + "0" * (len(str(_max_value)) - 1))
            _max_value = _max_value if _max_value >= 10 else 100
            _step = int(_max_value / 10)
            for i in range(_step, _max_value + _step, _step):
                _y_index.append(i)
            self.y_index = _y_index
        self._p = self.line_length / max(self.y_index)
        self._y_interval = int(self.line_length / len(self.y_index))

    def gen_graph(self):
        """
        说明:
            生成图像
        """
        self.markImg = self._init_graph(
            x_name=self.x_name,
            y_name=self.y_name,
            x_index=self.x_index,
            y_index=self.y_index,
            font_size=self.font_size,
            is_grid=self.is_grid,
        )
        if self.mat_type == "line":
            self._gen_line_graph(y=self.y, display_num=self.display_num)
        elif self.mat_type == "bar":
            self._gen_bar_graph(y=self.y, display_num=self.display_num)
        elif self.mat_type == "barh":
            self._gen_bar_graph(y=self.y, display_num=self.display_num, is_barh=True)

    def set_y(self, y: List[int]):
        """
        说明:
            给坐标点设置新值
        参数：
            :param y: 坐标点
        """
        self._check_value(y, self.y_index)
        self.y = y

    def set_y_index(self, y_index: List[Union[str, int, float]]):
        """
        说明:
            设置y轴坐标值
        参数：
            :param y_index: y轴坐标值
        """
        self._check_value(self.y, y_index)
        self.y_index = y_index

    def set_title(self, title: str, color: Optional[Union[str, Tuple[int, int, int]]]):
        """
        说明：
            设置标题
        参数：
            :param title: 标题
            :param color: 字体颜色
        """
        self.title = title
        if color:
            self._color["title"] = color

    def set_background(
        self, background: Optional[List[str]], type_: Optional[str] = None
    ):
        """
        说明：
            设置背景图片
        参数：
            :param background: 图片路径列表
            :param type_: 填充类型
        """
        self.background = background
        self.background_filler_type = type_ if type_ else self.background_filler_type

    def show(self):
        """
        说明：
            展示图像
        """
        self.markImg.show()

    def pic2bs4(self) -> str:
        """
        说明：
            转base64
        """
        return self.markImg.pic2bs4()

    def resize(self, ratio: float = 0.9):
        """
        说明：
            调整图像大小
        参数：
            :param ratio: 比例
        """
        self.markImg.resize(ratio * self.markImg.width, ratio * self.markImg.height)

    def save(self, path: Union[str, Path]):
        """
        说明：
            保存图片
        参数：
            :param path: 路径
        """
        self.markImg.save_file(path)

    def _check_value(
        self,
        y: List[int],
        y_index: List[Union[str, int, float]] = None,
        x_index: List[Union[str, int, float]] = None,
    ):
        """
        说明:
            检查值合法性
        参数：
            :param y: 坐标值
            :param y_index: y轴坐标值
            :param x_index: x轴坐标值
        """
        if y_index:
            _value = x_index if self.mat_type == "barh" else y_index
            if max(y) > max(y_index):
                raise ValueError("坐标点的值必须小于y轴坐标的最大值...")
            i = -9999999999
            for y in y_index:
                if y > i:
                    i = y
                else:
                    raise ValueError("y轴坐标值必须有序...")

    def _gen_line_graph(
        self,
        y: List[Union[int, float]],
        display_num: bool = False,
    ):
        """
        说明:
            生成折线图
        参数：
            :param y: 坐标点
            :param display_num: 显示该点的值
        """
        _black_point = IMG.new("RGBA", (7, 7), color=random.choice(self.bar_color)).circle()
        x_interval = self._x_interval
        current_w = self.padding_w + x_interval
        current_h = self.padding_h + self.line_length
        for i in range(len(y)):
            if display_num:
                w = int(Text2Image.from_text(
                    str(y[i]),
                    fontsize=self.font_size,
                    fontname=self.font
                ).width / 2)
                self.markImg.draw_text(
                    (
                        current_w - w,
                        current_h - int(y[i] * self._p * self._deviation) - 25 - 5,
                    ),
                    f"{y[i]:.2f}" if isinstance(y[i], float) else f"{y[i]}",
                    fontsize=self.font_size,
                    fontname=self.font
                )
            self.markImg.paste(
                _black_point,
                (
                    current_w - 3,
                    current_h - int(y[i] * self._p * self._deviation) - 3,
                ),
                True,
            )
            if i != len(y) - 1:
                self.markImg.draw_line(
                    (
                        current_w,
                        current_h - int(y[i] * self._p * self._deviation),
                        current_w + x_interval,
                        current_h - int(y[i + 1] * self._p * self._deviation),
                    ),
                    fill=(0, 0, 0),
                    width=2,
                )
            current_w += x_interval

    def _gen_bar_graph(
        self,
        y: List[Union[int, float]],
        display_num: bool = False,
        is_barh: bool = False,
    ):
        """
        说明：
            生成柱状图
        参数：
            :param y: 坐标值
            :param display_num: 是否显示数值
            :param is_barh: 横柱状图
        """
        _interval = self._x_interval
        if is_barh:
            current_h = self.padding_h + self.line_length - _interval
            current_w = self.padding_w
        else:
            current_w = self.padding_w + _interval
            current_h = self.padding_h + self.line_length

        font_h = Text2Image.from_text(
            str(y[0]),
            fontsize=self.font_size,
            fontname=self.font
        ).height
        for i in range(len(y)):
            # 画出显示数字
            if display_num:
                # 横柱状图
                if is_barh:
                    self.markImg.draw_text(
                        (
                            self.padding_w
                            + int(y[i] * self._p * self._deviation)
                            + 2
                            + 5,
                            current_h - int(font_h / 2) - 1,
                        ),
                        f"{y[i]:.2f}" if isinstance(y[i], float) else f"{y[i]}",
                        fontsize=self.font_size,
                        fontname=self.font
                    )
                else:
                    w = int(Text2Image.from_text(
                        str(y[i]),
                        fontsize=self.font_size,
                        fontname=self.font
                    ).width / 2)
                    self.markImg.draw_text(
                        (
                            current_w - w,
                            current_h - int(y[i] * self._p * self._deviation) - 25,
                        ),
                        f"{y[i]:.2f}" if isinstance(y[i], float) else f"{y[i]}",
                        fontsize=self.font_size,
                        fontname=self.font
                    )
            # 粘贴图形条
            if i != len(y):
                bar_color = random.choice(self.bar_color)
                # 横向粘贴
                if is_barh:
                    # 粘贴数字
                    A = IMG.new(
                        "RGBA",
                        (int(y[i] * self._p * self._deviation), self._bar_width),
                        color=bar_color
                    )
                    self.markImg.paste(
                        A,
                        (
                            current_w + 2,
                            current_h - int(self._bar_width / 2),
                        ),
                        True
                    )
                # 纵向粘贴
                else:
                    A = IMG.new(
                        "RGBA",
                        (self._bar_width, int(y[i] * self._p * self._deviation)),
                        color=bar_color
                    )
                    self.markImg.paste(
                        A,
                        (
                            current_w - int(self._bar_width / 2),
                            current_h - int(y[i] * self._p * self._deviation),
                        ),
                        True
                    )
            if is_barh:
                current_h -= _interval
            else:
                current_w += _interval

    def _init_graph(
        self,
        x_name: Optional[str] = None,
        y_name: Optional[str] = None,
        x_index: List[Union[str, int, float]] = None,
        y_index: List[Union[str, int, float]] = None,
        font_size: Optional[int] = None,
        is_grid: bool = False,
    ) -> IMG:
        """
        说明：
            初始化图像，生成xy轴
        参数：
            :param x_name: x轴名称
            :param y_name: y轴名称
            :param x_index: x轴坐标值
            :param y_index: y轴坐标值
            :param is_grid: 添加栅格
        """
        padding_w = self.padding_w
        padding_h = self.padding_h
        line_length = self.line_length
        background = random.choice(self.background) if self.background else None

        A = IMG.open(background).resize((self.w, self.h))
        if background:
            tmp = IMG.new("RGB", (self.w, self.h), color="white")
            tmp.transparent(2)
            A = A.paste(tmp, alpha=True)
        if self.title:
            title = Text2Image.from_text(
                self.title,
                fontsize=35,
                fontname=self.font,
                fill=self._color.get("title") if self._color.get("title") else "black",
            ).to_image()
            A.paste(title, (0, 25), True, center_type="by_width")
        A.draw_line(
            (
                padding_w,
                padding_h + line_length,
                padding_w + line_length,
                padding_h + line_length,
            ),
            (0, 0, 0),
            2,
        )
        A.draw_line(
            (
                padding_w,
                padding_h,
                padding_w,
                padding_h + line_length,
            ),
            (0, 0, 0),
            2,
        )
        _interval = self._x_interval
        if self.mat_type == "barh":
            x_index, y_index = y_index, x_index
            _interval = self._y_interval
        current_w = padding_w + _interval
        _grid = self.line_length if is_grid else 10
        x_rotate_height = 0
        for _x in x_index:
            _p = IMG.new("RGBA", (1, _grid), "#a9a9a9")
            A.paste(_p, (current_w, padding_h + line_length - _grid), True)
            text = Text2Image.from_text(
                f"{_x}",
                fontsize=self.font_size,
                fontname=self.font,
            ).to_image()
            w = int(text.width / 2)
            text.rotate(self.x_rotate, expand=True)
            A.paste(text, (current_w - w, padding_h + line_length + 10), alpha=True)
            current_w += _interval
            x_rotate_height = text.height
        _interval = self._x_interval if self.mat_type == "barh" else self._y_interval
        current_h = padding_h + line_length - _interval
        for _y in y_index:
            _p = IMG.new("RGBA", (_grid, 1), "#a9a9a9")
            A.paste(_p, (padding_w + 2, current_h), True)
            text = Text2Image.from_text(
                f"{_y}",
                fontsize=self.font_size,
                fontname=self.font,
            ).to_image()
            w, h = text.size
            h = int(h / 2)
            idx = 0
            while text.size[0] > self.padding_w - 10 and idx < 5:
                text = Text2Image.from_text(
                    f"{_y}",
                    fontsize=int(self.font_size * 0.75),
                    fontname=self.font,
                ).to_image()
                w, _ = text.size
                idx += 1
            A.paste(text, (padding_w - w - 10, current_h - h), alpha=True)
            current_h -= _interval
        if x_name:
            A.draw_text((int(padding_w / 2), int(padding_w / 2)), x_name)
        if y_name:
            y_name_textimg = Text2Image.from_text(
                y_name,
                fontsize=font_size,
                fontname=self.font,
            )
            A.draw_text(
                (
                    int(padding_w + line_length + 50 - y_name_textimg.width),
                    int(padding_h + line_length + 50 + x_rotate_height),
                ),
                y_name,
            )
        return A
