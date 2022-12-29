from typing import Tuple, Union
from typing_extensions import Literal


ModeType = Literal[
    "1", "CMYK", "F", "HSV", "I", "L", "LAB", "P", "RGB", "RGBA", "RGBX", "YCbCr"
]
ColorType = Union[str, Tuple[int, int, int], Tuple[int, int, int, int]]
PosTypeFloat = Tuple[float, float]
PosTypeInt = Tuple[int, int]
CenterType = Literal["center", "by_height", "by_width"]
XYType = Union[Tuple[float, float, float, float], Tuple[float, float]]  # 左，上，右，下
BoxType = Tuple[int, int, int, int]
PointsTYpe = Tuple[PosTypeFloat, PosTypeFloat, PosTypeFloat, PosTypeFloat]
DistortType = Tuple[float, float, float, float]
SizeType = Tuple[int, int]
HAlignType = Literal["left", "right", "center"]
VAlignType = Literal["top", "bottom", "center"]
OrientType = Literal["horizontal", "vertical"]
DirectionType = Literal[
    "center",
    "north",
    "south",
    "west",
    "east",
    "northwest",
    "northeast",
    "southwest",
    "southeast",
]
ResampleType = Literal[0, 1, 2, 3, 4, 5]
TransposeType = Literal[0, 1, 2, 3, 4, 5, 6]

FontStyle = Literal["normal", "italic", "oblique"]
FontWeight = Literal["ultralight", "light", "normal", "bold", "ultrabold", "heavy"]
