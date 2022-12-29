import math
from enum import Enum

from utils.http_utils import AsyncHttpx
import imageio
from io import BytesIO
from dataclasses import dataclass
from PIL.Image import Image as IMG
from typing_extensions import Literal
from typing import Callable, List, Tuple, Protocol
from nonebot.utils import run_sync
from utils.imageutils import BuildImage, Text2Image


@dataclass
class UserInfo:
    qq: str = ""
    group: str = ""
    name: str = ""
    gender: Literal["male", "female", "unknown"] = "unknown"
    img_url: str = ""
    img: BuildImage = BuildImage.new("RGBA", (640, 640))


@dataclass
class Command:
    func: Callable
    keywords: Tuple[str, ...]
    pattern: str = ""
    arg_type: str = "NoArg"

    def __post_init__(self):
        if not self.pattern:
            self.pattern = "|".join(self.keywords)


def save_gif(frames: List[IMG], duration: float) -> BytesIO:
    output = BytesIO()
    imageio.mimsave(output, frames, format="gif", duration=duration)
    return output


class Maker(Protocol):
    def __call__(self, img: BuildImage) -> BuildImage:
        ...


class GifMaker(Protocol):
    def __call__(self, i: int) -> Maker:
        ...


def get_avg_duration(image: IMG) -> float:
    if not getattr(image, "is_animated", False):
        return 0
    total_duration = 0
    for i in range(image.n_frames):
        image.seek(i)
        total_duration += image.info["duration"]
    return total_duration / image.n_frames


def make_jpg_or_gif(
    img: BuildImage, func: Maker, gif_zoom: float = 1, gif_max_frames: int = 50, isreverse: bool = False
) -> BytesIO:
    """
    制作静图或者动图
    :params
      * ``img``: 输入图片，如头像
      * ``func``: 图片处理函数，输入img，返回处理后的图片
      * ``gif_zoom``: gif 图片缩放比率，避免生成的 gif 太大
      * ``gif_max_frames``: gif 最大帧数，避免生成的 gif 太大
    """
    image = img.image
    if not getattr(image, "is_animated", False):
        return func(img.convert("RGBA")).save_jpg()
    else:
        index = [i for i in range(image.n_frames)]
        ratio = image.n_frames / gif_max_frames
        duration = image.info["duration"] / 1000
        if ratio > 1:
            index = [int(i * ratio) for i in range(gif_max_frames)]
            duration *= ratio

        frames = []
        index = [i for i in index[::-1]] if isreverse else index
        for i in index:
            image.seek(i)
            new_img = func(BuildImage(image).convert("RGBA"))
            frames.append(
                new_img.resize(
                    (int(new_img.width * gif_zoom), int(new_img.height * gif_zoom))
                ).image
            )
        return save_gif(frames, duration)


class FrameAlignPolicy(Enum):
    """
    要叠加的gif长度大于基准gif时，是否延长基准gif长度以对齐两个gif
    """

    no_extend = 0
    """不延长"""
    extend_first = 1
    """延长第一帧"""
    extend_last = 2
    """延长最后一帧"""
    extend_loop = 3
    """以循环方式延长"""


def make_gif_or_combined_gif(
    img: BuildImage,
    maker: GifMaker,
    frame_num: int,
    duration: float,
    frame_align: FrameAlignPolicy = FrameAlignPolicy.no_extend,
    input_based: bool = False,
    keep_transparency: bool = False,
) -> BytesIO:
    """
    使用静图或动图制作gif
    :params
      * ``img``: 输入图片，如头像
      * ``maker``: 图片处理函数生成，传入第几帧，返回对应的图片处理函数
      * ``frame_num``: 目标gif的帧数
      * ``duration``: 相邻帧之间的时间间隔，单位为秒
      * ``frame_align``: 要叠加的gif长度大于基准gif时，gif长度对齐方式
      * ``input_based``: 是否以输入gif为基准合成gif，默认为`False`，即以目标gif为基准
      * ``keep_transparency``: 传入gif时，是否保留该gif的透明度
    """
    image = img.image
    if not getattr(image, "is_animated", False):
        return save_gif([maker(i)(img).image for i in range(frame_num)], duration)

    frame_num_in = image.n_frames
    duration_in = get_avg_duration(image) / 1000
    total_duration_in = frame_num_in * duration_in
    total_duration = frame_num * duration

    if input_based:
        frame_num_base = frame_num_in
        frame_num_fit = frame_num
        duration_base = duration_in
        duration_fit = duration
        total_duration_base = total_duration_in
        total_duration_fit = total_duration
    else:
        frame_num_base = frame_num
        frame_num_fit = frame_num_in
        duration_base = duration
        duration_fit = duration_in
        total_duration_base = total_duration
        total_duration_fit = total_duration_in

    frame_idxs: List[int] = list(range(frame_num_base))
    diff_duration = total_duration_fit - total_duration_base
    diff_num = int(diff_duration / duration_base)

    if diff_duration >= duration_base:
        if frame_align == FrameAlignPolicy.extend_first:
            frame_idxs = [0] * diff_num + frame_idxs

        elif frame_align == FrameAlignPolicy.extend_last:
            frame_idxs += [frame_num_base - 1] * diff_num

        elif frame_align == FrameAlignPolicy.extend_loop:
            frame_num_total = frame_num_base
            # 重复基准gif，直到两个gif总时长之差在1个间隔以内，或总帧数超出最大帧数
            while (
                frame_num_total + frame_num_base <= 100
            ):
                frame_num_total += frame_num_base
                frame_idxs += list(range(frame_num_base))
                multiple = round(frame_num_total * duration_base / total_duration_fit)
                if (
                    math.fabs(
                        total_duration_fit * multiple - frame_num_total * duration_base
                    )
                    <= duration_base
                ):
                    break

    frames: List[IMG] = []
    frame_idx_fit = 0
    time_start = 0
    for i, idx in enumerate(frame_idxs):
        while frame_idx_fit < frame_num_fit:
            if (
                frame_idx_fit * duration_fit
                <= i * duration_base - time_start
                < (frame_idx_fit + 1) * duration_fit
            ):
                if input_based:
                    idx_in = idx
                    idx_maker = frame_idx_fit
                else:
                    idx_in = frame_idx_fit
                    idx_maker = idx

                func = maker(idx_maker)
                image.seek(idx_in)
                frames.append(func(BuildImage(image.copy())).image)
                break
            else:
                frame_idx_fit += 1
                if frame_idx_fit >= frame_num_fit:
                    frame_idx_fit = 0
                    time_start += total_duration_fit

    if keep_transparency:
        image.seek(0)
        if image.info.__contains__("transparency"):
            frames[0].info["transparency"] = image.info["transparency"]

    return save_gif(frames, duration)


async def translate(text: str) -> str:
    url = f"http://fanyi.youdao.com/translate"
    params = {"type": "ZH_CN2JA", "i": text, "doctype": "json"}
    try:
        resp = await AsyncHttpx.get(url, params=params)
        result = resp.json()
        return result["translateResult"][0][0]["tgt"]
    except:
        return ""


@run_sync
def help_image(commands: List[Command]) -> BytesIO:
    def cmd_text(cmds: List[Command], start: int = 1) -> str:
        return "\n".join(
            [f"{i + start}. " + "/".join(cmd.keywords) for i, cmd in enumerate(cmds)]
        )

    text1 = "摸头等头像相关表情制作\n触发方式：指令 + @某人 / qq号 / 自己 / [图片]\n支持的指令："
    idx = math.ceil(len(commands) / 3)
    text2 = cmd_text(commands[:idx])
    text3 = cmd_text(commands[idx: int(2 * idx)], start=idx + 1)
    text4 = cmd_text(commands[int(2 * idx):], start=int(2 * idx) + 1)
    img1 = Text2Image.from_text(text1, 30, weight="bold").to_image(padding=(20, 10))
    img2 = Text2Image.from_text(text2, 30).to_image(padding=(20, 10))
    img3 = Text2Image.from_text(text3, 30).to_image(padding=(20, 10))
    img4 = Text2Image.from_text(text4, 30).to_image(padding=(20, 10))
    w = max(img1.width, img2.width + img3.width + img4.width)
    h = img1.height + max(img2.height, img3.height, img4.height)
    img = BuildImage.new("RGBA", (w, h), "white")
    img.paste(img1, alpha=True)
    img.paste(img2, (0, img1.height), alpha=True)
    img.paste(img3, (img2.width, img1.height), alpha=True)
    img.paste(img4, (img2.width + img3.width, img1.height), alpha=True)
    return img.save_jpg()



@run_sync
def help_pic_image() -> BytesIO:
    def cmd_text(cmds: List, start: int = 1) -> str:
        return "\n".join(
            [f"{i + start}. " + cmd for i, cmd in enumerate(cmds)]
        )
    opera_list = ["倒放", "水平翻转", "垂直翻转", "黑白", "旋转", "反相", "浮雕", "轮廓", "锐化"]
    text1 = "触发方式：改图/图片操作 + 指令 + @user/qq/自己/图片\n* 已知透明背景动图作图效果不佳，存在首帧闪烁、透明背景填充杂色的问题 *\n图片操作所支持的指令如下："
    img1 = Text2Image.from_text(text1, 30, weight="bold").to_image(padding=(20, 10))
    text2 = cmd_text(opera_list)
    img2 = Text2Image.from_text(text2, 30).to_image(padding=(20, 10))
    w = max(img1.width, img2.width)
    h = img1.height + img2.height
    img = BuildImage.new("RGBA", (w, h), "white")
    img.paste(img1, alpha=True)
    img.paste(img2, (0, img1.height), alpha=True)
    return img.save_jpg()
