import io
import os
import random
import nonebot
from nonebot import Driver
from PIL import Image
from pathlib import Path
from typing import List, Dict
from services.log import logger
from configs.path_config import IMAGE_PATH
from nonebot_plugin_htmlrender import template_to_pic
from utils.utils import get_matchers
from manager import group_manager

driver: Driver = nonebot.get_driver()

random_bk_path = IMAGE_PATH / "background" / "help" / "admin_help"

admin_help_image = IMAGE_PATH / 'admin_help_img.png'


@driver.on_bot_connect
async def init_task():
    if not group_manager.get_task_data():
        await group_manager.init_group_task()
        logger.info(f'已成功加载 {len(group_manager.get_task_data())} 个被动技能.')


async def create_help_image():
    """
    异步 创建管理员帮助图片
    """
    _plugins_data: Dict[str, List[str]] = {}
    _plugin_types: List[str] = []
    _tmp = []
    cnt = 0
    for matcher in get_matchers():
        if matcher.plugin_name in _tmp:
            continue
        _tmp.append(matcher.plugin_name)
        _plugin = nonebot.plugin.get_plugin(matcher.plugin_name)
        _module = _plugin.module
        try:
            plugin_name = _module.__getattribute__("__plugin_name__")
            plugin_type =_module.__getattribute__("__plugin_type__")
        except AttributeError:
            continue
        try:
            if "[admin]" in plugin_name.lower():
                plugin_name = plugin_name.lower().replace("[admin]", "")
                plugin_settings = _module.__getattribute__("__plugin_settings__")
                admin_level = plugin_settings.get("admin_level", 0)
                if _plugins_data.get(plugin_type):
                    _plugins_data[plugin_type].append(f"[{admin_level}] {plugin_name}")
                else:
                    _plugins_data[plugin_type] = [f"[{admin_level}] {plugin_name}"]
                cnt += 1
            elif (
                "[hidden]" in plugin_name.lower()
                or "[superuser]" in plugin_name.lower()
                or plugin_name == "帮助"
            ):
                continue
            else:
                if plugin_type not in _plugin_types:
                    _plugin_types.append(plugin_type)
        except AttributeError:
            logger.warning(f"获取管理插件 {matcher.plugin_name}: {plugin_name} 设置失败...")
    # 总体开关功能
    _plugins_data["总体开关"] = _plugins_data.get("总体开关", [])
    for x in _plugin_types:
        _plugins_data["总体开关"].append(f"开启/关闭{x}")

    # 被动功能
    task_data = group_manager.get_task_data()
    _plugins_data["被动开关"] = _plugins_data.get("被动开关", [])
    for x in task_data.keys():
        _plugins_data["被动开关"].append(f"开启/关闭{task_data[x]}")

    # 生成图片
    random_bk = random.choice(os.listdir(random_bk_path))
    template_path = str(Path(__file__).parent / "templates")
    pic = await template_to_pic(
        template_path=template_path,
        template_name="help.html",
        templates={
            "bk": random_bk,
            "data": _plugins_data,
        },
        pages={
            "base_url": f"file://{template_path}",
        },
        wait=0,
    )
    Image.open(io.BytesIO(pic)).save(admin_help_image)
    logger.info(f"已成功加载 {cnt} 条管理命令")

