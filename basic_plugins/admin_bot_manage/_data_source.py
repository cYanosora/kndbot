from typing import List, Dict
from pathlib import Path
from datetime import datetime
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.adapters.onebot.v11 import Bot
from services.db_context import db
from services.log import logger
from configs.path_config import DATA_PATH
from models.level_user import LevelUser
from models.group_member_info import GroupInfoUser
from manager import group_manager, plugins2settings_manager, plugins_manager, Config
from utils.imageutils import BuildImage as IMG
from utils.http_utils import AsyncHttpx
from utils.message_builder import image
from utils.utils import get_matchers
import asyncio
import time
import os
try:
    import ujson as json
except ModuleNotFoundError:
    import json

custom_welcome_msg_json = (
    Path() / "data" / "custom_welcome_msg" / "custom_welcome_msg.json"
)
task_data = None
fontname = "SourceHanSansCN-Regular.otf"


async def group_current_status(group_id: int) -> str:
    """
    获取当前所有通知的开关
    :param group_id: 群号
    """
    rst = "  被动技能\n"
    flag_str = "状态".rjust(4) + "\n"
    _data = group_manager.get_task_data()
    for task in _data.keys():
        rst += f' {_data[task]}\n'
        flag_str += f'{"OPEN" if await group_manager.check_group_task_status(group_id, task) else "CLOSE"}\n'

    height = len(rst.split("\n")) * 30
    # 粘贴被动技能名
    a = IMG.new("RGBA", (280, height), "white")
    a.draw_text((10, 10), rst, fontsize=20, fontname=fontname, ischeckchar=False)
    # 粘贴被动功能状态

    b = IMG.new("RGBA", (280, height), "white")
    b.draw_text((10, 10), flag_str, fontsize=20, fontname=fontname, ischeckchar=False)
    # 合并图片
    A = IMG.new("RGBA", (400, height))
    A.paste(a)
    A.paste(b, (270, 0))
    return image(b64=A.pic2bs4())


async def custom_group_welcome(
    msg: str, imgs: List[str], user_id: int, group_id: int
) -> str:
    """
    替换群欢迎消息
    :param msg: 欢迎消息文本
    :param imgs: 欢迎消息图片，只取第一张
    :param user_id: 用户id，用于log记录
    :param group_id: 群号
    """
    img_result = ""
    img = imgs[0] if imgs else ""
    result = ""
    if (DATA_PATH / f"custom_welcome_msg/{group_id}.jpg").exists():
        (DATA_PATH / f"custom_welcome_msg/{group_id}.jpg").unlink()
    if not custom_welcome_msg_json.exists():
        custom_welcome_msg_json.parent.mkdir(parents=True, exist_ok=True)
        data = {}
    else:
        try:
            data = json.load(open(custom_welcome_msg_json, "r", encoding="utf-8"))
        except FileNotFoundError:
            data = {}
    try:
        if msg:
            data[str(group_id)] = str(msg)
            json.dump(
                data, open(custom_welcome_msg_json, "w", encoding="utf-8"), indent=4, ensure_ascii=False
            )
            logger.info(f"USER {user_id} GROUP {group_id} 更换群欢迎消息 {msg}")
            result += msg
        if img:
            await AsyncHttpx.download_file(
                img, DATA_PATH / "custom_welcome_msg" / f"{group_id}.jpg"
            )
            img_result = image(DATA_PATH / "custom_welcome_msg" / f"{group_id}.jpg")
            logger.info(f"USER {user_id} GROUP {group_id} 更换群欢迎消息图片")
    except Exception as e:
        logger.error(f"GROUP {group_id} 替换群消息失败 e:{e}")
        return "替换群欢迎消息失败.."
    return f"替换群欢迎消息成功：\n{result}" + img_result


async def del_group_welcome(user_id: int, group_id: int) -> str:
    """
    恢复默认群欢迎消息
    :param user_id: 用户id，用于log记录
    :param group_id: 群号
    """
    if (DATA_PATH / f"custom_welcome_msg/{group_id}.jpg").exists():
        (DATA_PATH / f"custom_welcome_msg/{group_id}.jpg").unlink()
    if custom_welcome_msg_json.exists():
        try:
            data = json.load(open(custom_welcome_msg_json, "r", encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        try:
            if data.get(str(group_id)):
                data.pop(str(group_id))
                json.dump(
                    data, open(custom_welcome_msg_json, "w", encoding="utf-8"), indent=4, ensure_ascii=False
                )
                logger.info(f"USER {user_id} GROUP {group_id} 删除群欢迎消息")
        except Exception as e:
            logger.error(f"GROUP {group_id} 删除群消息失败 e:{e}")
            return "删除群欢迎消息失败.."
    return f"删除群欢迎消息成功！"


async def get_plugin_group_status(cmd: str, status: bool) -> Dict[str, List[int]]:
    """
    获取插件在各群的开关状态(不统计超管)
    :param cmd:功能名称
    :param status:开关状态，True时获取打开功能的群号
    :returns: dict(模块名:群号列表)
    """
    global task_data
    if not task_data:
        task_data = group_manager.get_task_data()
    plugin_status = {}
    if cmd in [task_data[x] for x in task_data.keys()]:
        type_ = "task"
        modules = [x for x in task_data.keys() if task_data[x] == cmd]
    else:
        type_ = "plugin"
        modules = plugins2settings_manager.get_plugin_module(cmd, True)
    groups = group_manager.get_group_list()
    for module in modules:
        if type_ == 'task':
            plugin_status[task_data[module]] = []
            for group_id in groups:
                _status = await group_manager.check_group_task_status(group_id, module)
                if not (status ^ _status):
                    plugin_status[task_data[module]].append(group_id)
        else:
            plugin_status[module] = []
            for group_id in groups:
                _status = group_manager.get_plugin_status(module, group_id, False)
                if not (status ^ _status):
                    plugin_status[module].append(group_id)
    return plugin_status


async def change_group_switch(cmd: str, group_id: int, is_super: bool = False):
    """
    修改群功能状态
    :param cmd: 功能名称
    :param group_id: 群号
    :param is_super: 是否位超级用户，超级用户用于私聊开关某群功能状态
    """
    global task_data
    if not task_data:
        task_data = group_manager.get_task_data()
    group_help_file = DATA_PATH / "group_help" / f"{group_id}.png"
    status = cmd[:2].strip()
    cmd = cmd[2:].strip()
    if cmd == "全部被动":
        for task in task_data:
            if status == "开启":
                if not await group_manager.check_group_task_status(group_id, task):
                    await group_manager.open_group_task(group_id, task)
            else:
                if await group_manager.check_group_task_status(group_id, task):
                    await group_manager.close_group_task(group_id, task)
        if group_help_file.exists():
            group_help_file.unlink()
        return f"已 {status} 全部被动技能！"
    if cmd == "全部功能":
        for f in plugins2settings_manager.get_data():
            if status == "开启":
                group_manager.unblock_plugin(f, group_id)
            else:
                group_manager.block_plugin(f, group_id)
        if group_help_file.exists():
            group_help_file.unlink()
        return f"已 {status} 全部功能！"
    if cmd in [task_data[x] for x in task_data.keys()]:
        type_ = "task"
        modules = [x for x in task_data.keys() if task_data[x] == cmd]
    else:
        type_ = "plugin"
        modules = plugins2settings_manager.get_plugin_module(cmd, True)
    reply = ""
    cnt = 0
    for module in modules:
        # 群被动与一般插件分开处理
        if status == "开启":
            if type_ == "task":
                if await group_manager.check_group_task_status(group_id, module):
                    cnt += 1
                    reply = f"被动 {task_data[module]} 正处于开启状态！不要重复开启."
                else:
                    await group_manager.open_group_task(group_id, module)
            else:
                if group_manager.get_plugin_status(module, group_id):
                    cnt += 1
                    reply = f"功能 {cmd} 正处于开启状态！不要重复开启."
                else:
                    group_manager.unblock_plugin(
                        (f"{module}:super" if is_super else module), group_id
                    )
        else:
            if type_ == "task":
                if not await group_manager.check_group_task_status(group_id, module):
                    cnt += 1
                    reply = f"被动 {task_data[module]} 正处于关闭状态！不要重复关闭."
                else:
                    await group_manager.close_group_task(group_id, module)
            else:
                if not group_manager.get_plugin_status(module, group_id):
                    cnt += 1
                    reply = f"功能 {cmd} 正处于关闭状态！不要重复关闭."
                else:
                    group_manager.block_plugin(
                        (f"{module}:super" if is_super else module), group_id
                    )
    reply = reply if cnt == len(modules) else None
    if not reply and group_help_file.exists():
        group_help_file.unlink()
    return reply if reply else f"{status} {cmd} 功能！"


async def set_plugin_status(bot: Bot, cmd: str, block_type: str = "all"):
    """
    设置插件功能限制状态（超级用户使用）
    :param bot: Bot
    :param cmd: 功能名称
    :param block_type: 限制类型, 'all': 私聊+群聊, 'private': 私聊, 'group': 群聊
    """
    global task_data
    if not task_data:
        task_data = group_manager.get_task_data()
    status = cmd[:2].strip()
    cmd = cmd[2:].strip()
    if cmd in [task_data[x] for x in task_data.keys()]:
        type_ = "task"
        modules = [x for x in task_data.keys() if task_data[x] == cmd]
    else:
        type_ = "plugin"
        modules = plugins2settings_manager.get_plugin_module(cmd, True)
    for module in modules:
        if type_ == "plugin":
            if status == "开启":
                plugins_manager.unblock_plugin(module)
            else:
                plugins_manager.block_plugin(module, block_type=block_type)
            for file in os.listdir(DATA_PATH / "group_help"):
                file = DATA_PATH / "group_help" / file
                file.unlink()
        else:
            gl = [g["group_id"] for g in await bot.get_group_list()]
            if status == "开启":
                for group_id in gl:
                    await group_manager.open_group_task(group_id, module)
            else:
                for group_id in gl:
                    await group_manager.close_group_task(group_id, module)


async def get_plugin_status():
    """
    异步 获取功能状态
    """
    return await asyncio.get_event_loop().run_in_executor(None, _get_plugin_status)


def _get_plugin_status() -> MessageSegment:
    """
    合成功能状态图片
    """
    global fontname
    rst = "  功能\n"
    flag_str = "状态".rjust(4) + "\n"
    tmp_name = []
    for matcher in get_matchers():
        if matcher.plugin_name not in tmp_name:
            tmp_name.append(matcher.plugin_name)
            module = matcher.plugin_name
            flag = plugins_manager.get_plugin_block_type(module)
            flag = flag.upper() + " CLOSE" if flag else "OPEN"
            try:
                plugin_name = plugins_manager.get(module)["plugin_name"]
                if (
                    "[hidden]" in plugin_name.lower()
                    or "[admin]" in plugin_name.lower()
                    or "[superuser]" in plugin_name.lower()
                ):
                    continue
                rst += f"{plugin_name}"
            except KeyError:
                rst += f"{module}"
            if plugins_manager.get(module)["error"]:
                rst += "[ERROR]"
            rst += "\n"
            flag_str += f"{flag}\n"
    height = len(rst.split("\n")) * 30
    a = IMG.new("RGBA", (250, height))
    a.draw_text((0, 0), rst, fontsize=20, fontname=fontname, ischeckchar=False)
    b = IMG.new("RGBA", (100, height))
    b.draw_text((0, 0), flag_str, fontsize=20, fontname=fontname, ischeckchar=False)
    A = IMG.new("RGBA", (400, height))
    A.paste(a, (10, 10))
    A.paste(b, (280, 10))
    return image(b64=A.pic2bs4())


async def update_member_info(bot: Bot, group_id: int, remind_superuser: bool = False) -> bool:
    """
    更新群成员信息
    :param bot: Bot
    :param group_id: 群号
    :param remind_superuser: 失败信息提醒超级用户
    """
    _group_user_list = await bot.get_group_member_list(group_id=group_id)
    _error_member_list = []
    _exist_member_list = []
    # try:
    for user_info in _group_user_list:
        if user_info["card"] == "":
            nickname = user_info["nickname"]
        else:
            nickname = user_info["card"]
        async with db.transaction():
            # 更新权限
            if (
                user_info["role"]
                in [
                    "owner",
                    "admin",
                ]
                and not await LevelUser.is_group_flag(user_info["user_id"], group_id)
            ):
                await LevelUser.set_level(
                    user_info["user_id"],
                    user_info["group_id"],
                    Config.get_config("admin_bot_manage", "ADMIN_DEFAULT_AUTH"),
                )
            if str(user_info["user_id"]) in bot.config.superusers:
                await LevelUser.set_level(
                    user_info["user_id"], user_info["group_id"], 9
                )
            # 更新群组成员信息列表
            user = await GroupInfoUser.get_member_info(
                user_info["user_id"], user_info["group_id"]
            )
            if user:
                if user.user_name != nickname:
                    await user.update(user_name=nickname).apply()
                    logger.info(
                        f"用户{user_info['user_id']} 所属{user_info['group_id']} 更新群昵称成功"
                    )
                _exist_member_list.append(int(user_info["user_id"]))
                continue
            join_time = datetime.strptime(
                time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(user_info["join_time"])
                ),
                "%Y-%m-%d %H:%M:%S",
            )
            if await GroupInfoUser.add_member_info(
                user_info["user_id"],
                user_info["group_id"],
                nickname,
                join_time,
            ):
                _exist_member_list.append(int(user_info["user_id"]))
                logger.info(f"用户{user_info['user_id']} 所属{user_info['group_id']} 更新成功")
            else:
                _error_member_list.append(
                    f"用户{user_info['user_id']} 所属{user_info['group_id']} 更新失败\n"
                )
    # 删除已退群群员信息列表
    _del_member_list = list(
        set(_exist_member_list).difference(
            set(await GroupInfoUser.get_group_member_id_list(group_id))
        )
    )
    if _del_member_list:
        for del_user in _del_member_list:
            if await GroupInfoUser.delete_member_info(del_user, group_id):
                logger.info(f"退群用户{del_user} 所属{group_id} 已删除")
            else:
                logger.info(f"退群用户{del_user} 所属{group_id} 删除失败")
    if _error_member_list and remind_superuser:
        result = ""
        for error_user in _error_member_list:
            result += error_user
        await bot.send_private_msg(
            user_id=int(list(bot.config.superusers)[0]), message=result[:-1]
        )
    return True


def set_group_bot_status(group_id: int, status: bool) -> str:
    """
    设置群聊bot开关状态
    :param group_id: 群号
    :param status: 状态
    """
    if status:
        if group_manager.check_group_bot_status(group_id):
            reply = "嗯？我在工作呢..."
        else:
            group_manager.turn_on_group_bot_status(group_id)
            reply = "好的，我继续工作了..."
    else:
        if group_manager.check_group_bot_status(group_id):
            group_manager.shutdown_group_bot_status(group_id)
            reply = "那我先睡觉了..."
        else:
            reply = "嗯..我有在好好休息哦？"
    return reply
