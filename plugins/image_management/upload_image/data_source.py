import imghdr
import hashlib
from pathlib import Path
from nonebot.adapters.onebot.v11 import MessageSegment, Message
from configs.config import NICKNAME
from typing import List, Tuple, Union, Optional
from configs.path_config import IMAGE_PATH
from manager import Config
from services.log import logger
from utils.message_builder import image
from utils.utils import cn2py
from utils.http_utils import AsyncHttpx
import os
from .._model import ImageUpload


_path = IMAGE_PATH / "image_management"


async def get_local_record() -> int:
    """
    获取当前同人图记录数
    """
    all_gallerys = Config.get_config("image_management", "IMAGE_DIR_LIST")
    record_num = 0
    for gallery in all_gallerys:
        _gall = cn2py(gallery)
        path = _path / _gall
        for file in os.listdir(path):
            imgid = int(file.split('.')[0])
            if await ImageUpload.check_record(_gall, imgid):
                record_num += 1
    return record_num


async def record_local_images(target_gall: str, target_imgs: List[int]) -> str:
    """
    记录同人图
    """
    _gall = cn2py(target_gall)
    path = _path / _gall
    resolve_ids = []
    all_ids_suffixs = map(lambda x: os.path.splitext(x), os.listdir(path))
    all_ids_suffixs = filter(lambda x: x[0].isdigit() and int(x[0]) in target_imgs, all_ids_suffixs)
    for idsuf in all_ids_suffixs:
        img_id, suffix = idsuf
        file = path / f"{img_id}{suffix}"
        if file.exists():
            record = await ImageUpload.get_record(_gall, int(img_id))
            await ImageUpload.update_record(record, is_record=True)
            resolve_ids.append(str(img_id))
    reply = ''
    if resolve_ids:
        reply += f'收录成功{len(resolve_ids)}张图(id:' + ','.join(resolve_ids) + ')'
    if not reply:
        max_id = len(os.listdir(path))
        reply = f'没有有效图片id，当前{target_gall}图库共有{max_id}张图'
    return reply


async def upload_image_to_local(
    img_list: List[str], path_: str, user_id: int, group_id: int = 0
) -> Tuple[str, List[Union[str, MessageSegment, Message]]]:
    # 检查路径
    _path_name = cn2py(path_)
    path = _path / _path_name
    if not path.exists() and (path.parent.parent / _path_name).exists():
        path = path.parent.parent / _path_name
    path.mkdir(parents=True, exist_ok=True)
    all_files = os.listdir(path)
    curr_img_id = len(all_files) + 1
    success_list = []
    failed_list = []
    repeat_list = []
    mes_list = []
    for img_url in img_list:
        # 下载图片
        resp = await AsyncHttpx.get(img_url)
        suffix = imghdr.what(None, resp.content)
        save_file = path / f"{curr_img_id}.{suffix}"
        if resp.status_code == 200:
            content = resp.content
            # 简单去重
            md5_ = get_md5(content)
            repeat = False
            for i in all_files:
                compare_md5_ = get_md5(path=path / i)
                if md5_ == compare_md5_:
                    repeat = True
                    break
            if repeat:
                repeat_list.append(img_url)
                continue
            # 未重复，成功保存
            with open(save_file, 'wb') as f:
                f.write(content)
            success_list.append(str(curr_img_id))
            # 记录进数据库
            await ImageUpload.add_record(_path_name, curr_img_id, user_id, group_id)
            # 放入消息列表中
            mes_list.append(image(f"{_path_name}/{curr_img_id}.{suffix}", "image_management"))
            curr_img_id += 1
        # 下载失败
        else:
            failed_list.append(img_url)
    failed_result = ""
    for img in failed_list:
        failed_result += str(img) + "\n"
    # 日志记录
    log_info = f"用户({user_id}) 群({group_id}) 为 {_path_name}库 添加了{len(success_list)} 张图片"
    # 用户回显
    result = f"这次一共为 {path_}库 添加了{len(success_list)} 张图片"
    if success_list:
        result += f"\n依次的Id为：{','.join(success_list)}"
        log_info += f"\n依次的Id为：{','.join(success_list)}"
    if failed_list:
        result += f"\n上传失败{len(failed_list)}张"
        log_info += f"\n上传失败{len(failed_list)}张，网址：" + '\n'.join(failed_list)
    if repeat_list:
        result += f"\n重复{len(repeat_list)}张"
        log_info += f"\n上传失败{len(repeat_list)}张，网址：" + '\n'.join(repeat_list)
    if success_list:
        result += f"\n{NICKNAME}感谢您对图库的扩充!WW"
    logger.info(log_info)
    mes_list.insert(0, log_info)
    return result, mes_list


def get_md5(
    content: Optional[bytes] = None,
    path: Optional[Union[str, Path]] = None
):
    """
    计算图像的md5值
    """
    if not content and path:
        f = open(path, 'rb')
        content = f.read()
        f.close()
    if not content:
        raise ValueError("没有足够的参数")
    md5 = hashlib.md5(content)
    md5_values = md5.hexdigest()
    return md5_values