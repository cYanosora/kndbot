import io
import os
import random
from pathlib import Path
from typing import List, Dict
from PIL import Image
from nonebot_plugin_htmlrender import template_to_pic
from configs.path_config import IMAGE_PATH
from services.log import logger
from utils.utils import get_matchers
from nonebot import Driver
import nonebot


driver: Driver = nonebot.get_driver()

random_bk_path = IMAGE_PATH / "background" / "help" / "superuser_help"

background = IMAGE_PATH / "background" / "usage.jpg"

superuser_help_image = IMAGE_PATH / "superuser_help.png"


@driver.on_bot_connect
async def create_help_image():
    """
    异步 创建超级用户帮助图片
    """
    _plugins_data: Dict[str, List[str]] = {}
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
            plugin_type = _module.__getattribute__("__plugin_type__")
        except AttributeError:
            continue
        is_superuser_usage = False
        try:
            _ = _module.__getattribute__("__plugin_superuser_usage__")
            is_superuser_usage = True
        except AttributeError:
            pass
        try:
            if "[superuser]" in plugin_name.lower() or is_superuser_usage:
                plugin_name = plugin_name.lower().replace("[admin]", "").replace("[superuser]", "")
                if _plugins_data.get(plugin_type):
                    _plugins_data[plugin_type].append(plugin_name)
                else:
                    _plugins_data[plugin_type] = [plugin_name]
                cnt += 1
        except Exception as e:
            logger.warning(
                f"获取超级用户插件 {matcher.plugin_name}: {plugin_name} 设置失败... {type(e)}：{e}"
            )
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
    Image.open(io.BytesIO(pic)).save(superuser_help_image)
    logger.info(f"已成功加载 {cnt} 条超级用户命令")
