import os
import re
import time
from pathlib import Path
from typing import Union, List, Tuple
import numpy.random as random
from utils.message_builder import image
from .pjsk_db_source import PjskAlias
from .pjsk_config import *


# 用于rule匹配消息中是否含有图库名
async def pjsk_findin_db(msg: str, group_id: int ) -> Tuple[str, list]:
    for each in pjsk_info_all:
        if msg.startswith(each):
            return each, msg[len(each):].strip().replace(',', ' ').replace('，', ' ').split()
    name, rawids = await PjskAlias.query_name(msg, fuzzy_search=True, group_id=group_id)
    rawids = rawids.replace(',', ' ').replace('，', ' ').split()
    return name, rawids


def pjsk_get_path_and_len(name: str):
    path = ""
    # 查找团体图、单人图、特殊cp图、杂图
    for unit, chara in pjsk_info_dict.items():
        # 图库名为组合名
        if name == unit:
            # 对组合名为cp时做特殊处理
            if name == "cp":
                unit_cps = [j for i in pjsk_cp_dict.values() for j in i]
                out_cps = os.listdir(Path(pjsk_path) / "cp")
                cp = random.choice(out_cps + unit_cps)
                if cp in out_cps:
                    cp_unit = "cp"
                else:
                    cp_unit = [i for i in pjsk_cp_dict if cp in pjsk_cp_dict[i]][0] + '/cp'
                path = Path(pjsk_path) / cp_unit / cp
            elif name == "vs":
                path = Path(pjsk_path)/ unit / "cp"
            else:
                path = Path(pjsk_path)/ unit / "cp" / "other"
            break
        # 图库名为单人名
        elif name in chara:
            path = Path(pjsk_path) / unit / name
            break
    # 查找团内cp图
    else:
        for unit, charas in pjsk_cp_dict.items():
            if name in charas:
                path = Path(pjsk_path) / unit / "cp" / name
                break
    return path, len(os.listdir(path))


def pjsk_get_pic(path: Union[str, Path], img_ids: List = None):
    # 随机抽取一张图片发送
    if img_ids is None:
        img_ids = []

    # 图库文件排序
    def sort_key(path, file):
        rule = r'.+-\d+-(\d+_\d+)-.+'
        res = re.match(rule, file)
        if res:
            return time.mktime(time.strptime(res.group(1), "%Y%m%d_%H%M%S"))
        else:
            return False
    pic_list = sorted(os.listdir(Path(path)), reverse=True, key=lambda x: sort_key(path, x))
    # pic_list.sort(key=lambda x: x.split('.')[0])
    # pic_list.sort(key=lambda x: os.path.getctime(x))
    pic_len = len(pic_list)
    try:
        if img_ids:
            img_paths = [pic_list[i-1] for i in img_ids]
        else:
            img_ids = [random.randint(1, len(pic_list) + 1)]
            img_paths = [pic_list[img_ids[0] - 1]]
        result_list = []
        id = 0
        for img_path in img_paths:
            # 显示图片来源
            tag = re.search(r"(^\d+)(?:_p\d+)?.(jpg|png)", img_path)
            if tag:
                tag_type = f"pixiv id:{tag.group(1)}"
            else:
                tag = re.search(r"(.+)-\d+-\d+_\d+-img\d.(jpg|png)", img_path)
                if tag:
                    tag_type = f"Twitter@ {tag.group(1)}"
                else:
                    # 图源丢了
                    tag_type = ""
            result = path / img_path
            if not result:
                result_list.append(f"啊咧？序号为 {img_ids[id]} 的这张图不见了？")
            else:
                result_list.append(
                    image(result) + f"\n存量：{pic_len}  序号：{img_ids[id]}" +
                    (
                        f"\n{tag_type}" if tag_type else random.choice(
                            ["\n图源...诶？弄丢了（；´д｀）",
                             "\n图源未知，果咩那塞", ""]
                        )
                    )
                )
            id += 1
        return result_list
    except:
        return []


