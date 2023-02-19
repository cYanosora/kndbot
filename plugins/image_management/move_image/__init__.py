from services.log import logger
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message, GROUP
from manager import Config
from utils.utils import is_number, cn2py
from configs.path_config import IMAGE_PATH
from nonebot.params import CommandArg, ArgStr
import os
from .._model import ImageUpload

__plugin_name__ = "移动图片 [Admin]"
__plugin_type__ = "本地图库"
__plugin_version__ = 0.1
__plugin_usage__ = """
admin_usage：
    图库间的图片移动操作
    指令：
        移动图片 [源图库] [目标图库] [id]
    示例：
        移动图片 壁纸 美图 234
    注意：
        中途发送 "取消" 或者 "算了" 可以结束指令
""".strip()
__plugin_settings__ = {
    "admin_level": Config.get_config("image_management", "MOVE_IMAGE_LEVEL"),
    "cmd": ["移动图片"],
}


move_img = on_command("移动图片", priority=5, rule=to_me(), permission=GROUP, block=True)


_path = IMAGE_PATH / "image_management"


@move_img.handle()
async def _(state: T_State, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip().split()
    if args:
        if n := len(args):
            if args[0] in Config.get_config("image_management", "IMAGE_DIR_LIST"):
                state["source_path"] = args[0]
        if n > 1:
            if args[1] in Config.get_config("image_management", "IMAGE_DIR_LIST"):
                state["destination_path"] = args[1]
        if n > 2 and args[2].isdigit():
            state["id"] = args[2]


@move_img.got("source_path", prompt="要从哪个图库移出？")
@move_img.got("destination_path", prompt="要移动到哪个图库？")
@move_img.got("id", prompt="要移动的图片id是？")
async def _(
    event: MessageEvent,
    source_path: str = ArgStr("source_path"),
    destination_path: str = ArgStr("destination_path"),
    img_id: str = ArgStr("id"),
):
    # 取消操作
    if (
        source_path in ["取消", "算了"]
        or img_id in ["取消", "算了"]
        or destination_path in ["取消", "算了"]
    ):
        await move_img.finish("已取消操作...")
    # 检查参数
    if source_path not in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        await move_img.reject_arg("source_path", "移除目录不正确，请重新输入！")
    if destination_path not in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        await move_img.reject_arg("destination_path", "移入目录不正确，请重新输入！")
    if not img_id.isdigit():
        await move_img.reject_arg("id", "id不正确！请重新输入数字...")
    # 检查目录
    source_gall = cn2py(source_path)
    destination_gall = cn2py(destination_path)
    source_path = _path / source_gall
    destination_path = _path / destination_gall
    if not source_path.exists():
        if (source_path.parent.parent / source_gall).exists():
            source_path = source_path.parent.parent / source_gall
    if not destination_path.exists():
        if (destination_path.parent.parent / destination_gall).exists():
            destination_path = destination_path.parent.parent / destination_gall
    source_path.mkdir(exist_ok=True, parents=True)
    destination_path.mkdir(exist_ok=True, parents=True)
    # 检查源图库总量
    if not len(os.listdir(source_path)):
        await move_img.finish(f"{source_path}图库中没有任何图片，移动失败。")
    src_max_id = str(len(os.listdir(source_path)))
    des_max_id = str(len(os.listdir(destination_path)) + 1)
    # 检查源图库图片id是否超总量
    if int(img_id) > int(src_max_id) or int(img_id) <= 0:
        await move_img.finish(f"Id超过上下限，上限：{src_max_id}", at_sender=True)
    # 筛选文件名和后缀名
    all_ids_suffixs = list(map(lambda x: os.path.splitext(x), os.listdir(source_path)))
    src_ids_suffix = filter(lambda x: x[0].isdigit() and x[0] == img_id, all_ids_suffixs)
    max_ids_suffix = filter(lambda x: x[0].isdigit() and x[0] == src_max_id, all_ids_suffixs)
    _, src_suffix = next(src_ids_suffix)
    _, max_suffix = next(max_ids_suffix)
    # 移动图片
    try:
        move_file = source_path / f"{img_id}{src_suffix}"
        move_file.rename(destination_path / f"{des_max_id}{src_suffix}")
        if await ImageUpload.check_exists(source_gall, int(img_id)):
            record = await ImageUpload.get_record(source_gall, int(img_id))
            await ImageUpload.update_record(record, destination_gall, int(des_max_id))
        else:
            await ImageUpload.get_record(destination_gall, int(des_max_id))
        logger.info(
            f"移动 {source_path}/{img_id}{src_suffix} ---> {destination_path}/{des_max_id}{src_suffix} 移动成功"
        )
    except Exception as e:
        logger.warning(
            f"移动 {source_path}/{img_id}{src_suffix} ---> {destination_path}/{des_max_id}{src_suffix} 移动失败 e:{e}"
        )
        await move_img.finish(f"移动图片id：{img_id} 失败了...", at_sender=True)
    # 若源图库有其他图片
    if src_max_id != img_id:
        try:
            rep_file = source_path / f"{src_max_id}{max_suffix}"
            rep_file.rename(source_path / f"{img_id}{max_suffix}")
            if await ImageUpload.check_exists(source_gall, int(src_max_id)):
                record = await ImageUpload.get_record(source_gall, int(src_max_id))
                await ImageUpload.update_record(record, source_gall, int(img_id))
            else:
                await ImageUpload.get_record(source_gall, int(img_id))
            logger.info(f"{source_path}/{src_max_id}{max_suffix} 替换 {source_path}/{img_id}{max_suffix} 成功")
        except Exception as e:
            logger.warning(
                f"{source_path}/{src_max_id}{max_suffix} 替换 {source_path}/{img_id}{max_suffix} 失败 e:{e}"
            )
            await move_img.finish(f"替换图片id：{src_max_id} -> {img_id} 失败了...", at_sender=True)
    # 源图库只有一张图片
    else:
        await ImageUpload.del_record(source_gall, int(img_id))
    logger.info(
        f"USER {event.user_id} GROUP {event.group_id if isinstance(event, GroupMessageEvent) else 'private'} ->"
        f" {source_path} --> {destination_path} (id：{img_id}) 移动图片成功"
    )
    await move_img.finish(f"移动图片 id：{img_id} --> id：{des_max_id}成功", at_sender=True)
