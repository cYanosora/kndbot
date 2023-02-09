from nonebot.permission import SUPERUSER
from configs.path_config import IMAGE_PATH, TEMP_PATH
from utils.message_builder import image
from services.log import logger
from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message, GROUP
from utils.utils import is_number, cn2py
from manager import Config
from nonebot.params import CommandArg, Arg
import os
from .._model import ImageUpload

__plugin_name__ = "删除图片 [Admin]"
__plugin_type__ = "本地图库"
__plugin_version__ = 0.1
__plugin_usage__ = """
admin_usage：
    删除图库指定图片
    指令：
        删除图片 [图库] [id]
    示例：
        删除图片 美图 666
    注意：
        中途发送 "取消" 或者 "算了" 可以结束指令
""".strip()
__plugin_settings__ = {
    "admin_level": Config.get_config("image_management", "DELETE_IMAGE_LEVEL"),
    "cmd": ["删除图片"],
}


delete_img = on_command("删除图片", permission=GROUP | SUPERUSER, priority=5, block=True)


_path = IMAGE_PATH / "image_management"


@delete_img.handle()
async def _(state: T_State, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip().split()
    if args:
        if args[0] in Config.get_config("image_management", "IMAGE_DIR_LIST"):
            state["path"] = args[0]
        if len(args) > 1 and is_number(args[1]):
            state["id"] = args[1]


@delete_img.got("path", prompt="请输入要删除的目标图库？")
@delete_img.got("id", prompt="请输入要删除的图片id？")
async def arg_handle(
    event: MessageEvent,
    state: T_State,
    path: str = Arg("path"),
    img_id: str = Arg("id"),
):
    # 取消操作
    if path in ["取消", "算了"] or img_id in ["取消", "算了"]:
        await delete_img.finish("已取消操作...")
    # 检查图库
    if path not in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        await delete_img.reject_arg("path", "此目录不正确，请重新输入目录！")
    # 检查参数是否为数子
    if not is_number(img_id):
        await delete_img.reject_arg("id", "id不正确！请重新输入数字...")
    # 检查目录存在
    gallery = cn2py(path)
    path = _path / gallery
    if not path.exists() and (path.parent.parent / gallery).exists():
        path = path.parent.parent / gallery
    # 检查图片id是否超出图库总量
    max_id = len(os.listdir(path)) - 1
    if int(img_id) > max_id or int(img_id) < 0:
        await delete_img.finish(f"Id超过上下限，上限：{max_id}", at_sender=True)
    # 删除临时图片
    try:
        if (TEMP_PATH / "delete.jpg").exists():
            (TEMP_PATH / "delete.jpg").unlink()
        logger.info(f"删除{cn2py(state['path'])}图片 {img_id}.jpg 成功")
    except Exception as e:
        logger.warning(f"删除图片 delete.jpg 失败 e{e}")
    # 将原图库图片移动至临时文件夹等待自动删除
    try:
        os.rename(path / f"{img_id}.jpg", TEMP_PATH / f"{event.user_id}_delete.jpg")
        await ImageUpload.del_record(gallery, int(img_id))
        logger.info(f"移动 {path}/{img_id}.jpg 移动成功")
    except Exception as e:
        logger.warning(f"{path}/{img_id}.jpg --> 移动失败 e:{e}")
    # 若图库内不存在此图片，代表上述操作成功
    if not os.path.exists(path / f"{img_id}.jpg"):
        # 将最大id的图片替换为当前图片id
        try:
            if int(img_id) != max_id:
                os.rename(path / f"{max_id}.jpg", path / f"{img_id}.jpg")
                record = await ImageUpload.get_record(gallery, int(max_id))
                if record:
                    await ImageUpload.update_record(record, gallery, int(img_id))
        except FileExistsError as e:
            logger.error(f"{path}/{max_id}.jpg 替换 {path}/{img_id}.jpg 失败 e:{e}")
        else:
            logger.info(f"{path}/{max_id}.jpg 替换 {path}/{img_id}.jpg 成功")
        logger.info(
            f"USER {event.user_id} GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'}"
            f" -> id: {img_id} 删除成功"
        )
        await delete_img.finish(
            f"id: {img_id} 删除成功" + image(TEMP_PATH / f"{event.user_id}_delete.jpg",), at_sender=True
        )
    await delete_img.finish(f"id: {img_id} 删除失败！")
