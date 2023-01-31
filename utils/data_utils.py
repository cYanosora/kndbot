import datetime
import io
import math
import random
import time
from PIL import Image
from utils.utils import get_user_avatar
from models.group_member_info import GroupInfoUser
from utils.imageutils import BuildMat, BuildImage, union
from configs.path_config import IMAGE_PATH, TEMP_PATH
from typing import List, Union, Optional
import os


async def init_rank(
    title: str,
    all_user_id: List[int],
    all_user_data: List[int],
    group_id: int,
    total_count: int = 10,
    limit_count: int = 50,
    save_key: Optional[str] = None
):
    """
    说明：
        初始化通用的数据排行榜
    参数：
        :param title: 排行榜标题
        :param all_user_id: 所有用户的qq号
        :param all_user_data: 所有用户需要排行的对应数据
        :param group_id: 群号，用于从数据库中获取该用户在此群的昵称
        :param total_count: 获取人数总数，默认10
        :param limit_count: 限制的总人数，默认50
        :param save_key: 临时保存的排行榜图片文件名，不设置时排行榜即时生成
    """
    _uid_lst = []
    _uname_lst = []
    _num_lst = []
    for i in range(len(all_user_id) if len(all_user_id) < total_count else total_count):
        _max = max(all_user_data)
        max_user_id = all_user_id[all_user_data.index(_max)]
        all_user_id.remove(max_user_id)
        all_user_data.remove(_max)
        try:
            user_name = (
                await GroupInfoUser.get_member_info(max_user_id, group_id)
            ).user_name
        except AttributeError:
            user_name = f"{max_user_id}"
        _uid_lst.append(max_user_id)
        _uname_lst.append(user_name)
        _num_lst.append(_max)
    return await _init_rank_graph(title,_uid_lst,_uname_lst,_num_lst, limit_count, save_key)


async def _init_rank_graph(
    title: str,
    _uid_lst: List[int],
    _uname_lst: List[str],
    _num_lst: List[Union[int, float]],
    limit_count: int,
    save_key: Optional[str] = None
) -> BuildImage:
    """
    生成排行榜统计图
    :param title: 排行榜标题
    :param _uid_lst: 用户qq列表
    :param _uname_lst: 用户名列表
    :param _num_lst: 数值列表
    :param limit_count: 排行榜限制显示的人数
    :param save_key: 排行榜保存的临时文件名
    """
    if save_key is not None:
        save_path = TEMP_PATH / f"{save_key}.png"
        if save_path.exists():
            if save_path.stat().st_ctime + 3600 > time.time():
                return BuildImage.open(save_path)
            else:
                save_path.unlink()
    # 计算排行榜列数
    def warps(length, ratio) -> int:
        columns = 1
        height = 210
        width = 1680
        while True:
            last_ratio = width * columns / math.ceil(length * height / columns)
            if last_ratio < ratio * 0.5:
                columns += 1
            if last_ratio > ratio * 2 and columns > 1:
                columns -= 1
            now_ratio = width * columns / math.ceil(length * height / columns)
            if last_ratio == now_ratio:
                if last_ratio < ratio:
                    ratio_diff = abs(width * (columns+1) / math.ceil(length * height / (columns+1)) - ratio)
                    if ratio_diff < abs(last_ratio - ratio):
                        return columns + 1
                if last_ratio > ratio and columns > 1:
                    ratio_diff = abs(width * (columns-1) / math.ceil(length * height / (columns-1)) - ratio)
                    if ratio_diff < abs(last_ratio - ratio):
                        return columns - 1
                return columns
    bk_path = IMAGE_PATH / 'background' / 'create_mat'
    bkpic = BuildImage.open(bk_path / random.choice([i for i in os.listdir(bk_path) if not i.startswith('rank')]))
    ratio = bkpic.width/bkpic.height
    columns = warps(len(_uid_lst), ratio)
    # 排行榜标题图片
    titlesize = (1780 + 1810 * (columns-1), 180)
    titlepic = BuildImage.new('RGBA', titlesize, color='#bfd9ea')
    titlepic = titlepic.circle_corner(r=35)
    titlepic.draw_text((2, 2, titlesize[0]-720, 182), title, fontsize=80, fill="#eccfe1", halign='center', valign='center')
    titlepic.draw_text((0, 0, titlesize[0]-720, 180), title, fontsize=80, fill="#50555b", halign='center', valign='center')
    if save_key is None:
        titlepic.draw_text((titlesize[0] - 720, 0, titlesize[0], 180), f"* 可以在命令后添加数字来指定排行人数 至多{limit_count} *", fontsize=30,
                           fill="#50555b", valign='center')
    else:
        titlepic.draw_text((titlesize[0] - 720, 0, titlesize[0], 60), f"* 可以在命令后添加数字来指定排行人数 至多{limit_count} *", fontsize=30,
                           fill="#50555b", valign='center')
        titlepic.draw_text((titlesize[0]-720, 60, titlesize[0], 120), "* 相同排行榜限制每小时刷新一次 *", fontsize=30, fill="#50555b", valign='center')
        nowtime = datetime.datetime.strftime(datetime.datetime.now(), '%Y/%m/%d %H:%M')
        titlepic.draw_text((titlesize[0] - 720, 120, titlesize[0], 180), f"* 生成时间:{nowtime} *", fontsize=30, fill="#50555b",
                           valign='center')
    titlepic = titlepic.image
    oneranksize = (1680, 180)
    # 排行榜图片
    rankpics = []
    max_num = max(_num_lst)
    for i in range(len(_uid_lst)):
        max_bar_size = oneranksize[0]
        barlen = int(_num_lst[i] / max_num * max_bar_size)
        onerank = BuildImage.new("RGBA", oneranksize, color='white')
        if barlen > 0:
            onebar = BuildImage.open(bk_path / 'rankbar.png').resize((barlen, 180))
            onerank.paste(onebar, (0, 0), True)
        onerank = onerank.circle_corner(r=35)
        onerank.draw_rounded_rectangle((0, 0, 1680, 180), radius=35, outline='#8c8c8c', width=8)
        if i < 3:
            levelpic = Image.open(bk_path / f'rank{i+1}.png')
            onerank.paste(levelpic, (35, 26), alpha=True)
        else:
            onerank.draw_text((35, 26, 35+128,26+128),f"{i+1}",fontsize=80,fill="#00ccbb", halign='center', valign='center')
        avatarpic = await get_user_avatar(_uid_lst[i])
        avatarpic = BuildImage.open(io.BytesIO(avatarpic)).resize((128, 128))
        avatarpic = avatarpic.circle()
        onerank.paste(avatarpic, (198, 26), alpha=True)
        onerank.draw_text((233, 0, 1060, 180), f"{_uname_lst[i]}", fill="#4d4d4d", halign='center', valign='center')
        _num = format(_num_lst[i], '.3f') if str(int(_num_lst[i])) != format(_num_lst[i], '.5g') else str(int(_num_lst[i]))
        onerank.draw_text((1060, 0, 1680, 180), _num, fontsize=80, fill="#ff55aa", halign='center', valign='center')
        rankpics.append(onerank.image)
    # 合成排行榜图片
    picnum = math.ceil(len(rankpics) / columns)
    allrankpic = union(
        rankpics[:picnum], type='row', interval=25, bk_color='white',
        padding=(50, 50, 50, 50), border_type='circle'
    )
    for c in range(columns-1):
        _ = union(
            rankpics[picnum*(c+1):picnum*(c+2)], type='row', interval=25, bk_color='white',
            padding=(50, 50, 50, 50), border_type='circle'
        )
        allrankpic = union([allrankpic, _], type='col', interval=30, align_type='top')

    size = allrankpic.width + 240, allrankpic.height + titlepic.height + 180 + 30
    ratio = bkpic.width/bkpic.height
    bk_width = max(size[0], bkpic.width)
    bk_height = max(size[1], bkpic.height)
    if bk_width//ratio > bk_height:
        bkpic = bkpic.resize((bk_width, int(bk_width/ratio)))
    else:
        bkpic = bkpic.resize((int(bk_height*ratio), bk_height))
    tmp = BuildImage.open(bk_path / 'rankmask.png').resize(bkpic.size)
    bkpic.paste(tmp, alpha=True)
    bkpic.paste(
        union([titlepic, allrankpic], type='row', interval=30),
        (0,0), alpha=True, center_type="center"
    )
    if save_key is not None:
        bkpic.image.save(save_path)
    return bkpic


def _init_rank_graph_old(
    title: str, _uname_lst: List[str], _num_lst: List[Union[int, float]]
) -> BuildMat:
    """
    生成排行榜统计图
    :param title: 排行榜标题
    :param _uname_lst: 用户名列表
    :param _num_lst: 数值列表
    """
    image = BuildMat(
        y=_num_lst,
        y_name="* 可以在命令后添加数字来指定排行人数 至多 50 *",
        mat_type="barh",
        title=title,
        x_index=_uname_lst,
        display_num=True,
        x_rotate=30,
        background=[
            f"{IMAGE_PATH}/background/create_mat/{x}"
            for x in os.listdir(f"{IMAGE_PATH}/background/create_mat")
        ],
        bar_color=["*"],
    )
    image.gen_graph()
    return image
