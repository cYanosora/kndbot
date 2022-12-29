import io
import random
import nonebot
import os
from PIL import Image
from nonebot_plugin_htmlrender import template_to_pic
from utils.imageutils import BuildImage as IMG, Text2Image
from configs.path_config import IMAGE_PATH
from manager import (
    plugins2settings_manager,
    admin_manager,
    plugins_manager,
    group_manager, super_manager,
)
from typing import Optional
from services.log import logger
from pathlib import Path
from utils.utils import get_matchers


random_bk_path = IMAGE_PATH / "background" / "help" / "simple_help"

background = IMAGE_PATH / "background" / "usage.jpg"


async def create_help_img(
    group_id: Optional[int], simple_help_image: Path
):
    """
    异步 生成帮助图片
    :param group_id: 群号
    :param simple_help_image: 简易帮助图片路径
    """
    _plugins_data = {}
    _tmp = []
    # 插件分类
    for matcher in get_matchers():
        if matcher.plugin_name in _tmp:
            continue
        _tmp.append(matcher.plugin_name)
        plugin_name = None
        _plugin = nonebot.plugin.get_plugin(matcher.plugin_name)
        _module = _plugin.module
        try:
            # 只为通用插件生成帮助图
            plugin_name = _module.__getattribute__("__plugin_name__")
            if (
                "[hidden]" in plugin_name.lower()
                or "[admin]" in plugin_name.lower()
                or "[superuser]" in plugin_name.lower()
                or plugin_name == "帮助"
            ):
                continue
            # 获取插件类型
            plugin_type = "娱乐功能"
            if plugins2settings_manager.get(
                matcher.plugin_name
            ) and plugins2settings_manager[matcher.plugin_name].get("plugin_type"):
                plugin_type = plugins2settings_manager.get_plugin_data(
                        matcher.plugin_name
                    )["plugin_type"]
            else:
                try:
                    plugin_type = _module.__getattribute__("__plugin_type__")
                except AttributeError:
                    pass
            # 获取完插件信息，保存插件名数据，便于生成帮助图
            if plugin_type not in _plugins_data.keys():
                _plugins_data[plugin_type] = []
            _plugins_data[plugin_type].append(plugin_name)
        except AttributeError as e:
            logger.warning(f"获取功能 {matcher.plugin_name}: {plugin_name} 设置失败...e：{e}")
    # 获取完所有的插件帮助信息，开始生成帮助图
    types = list(_plugins_data.keys())
    types.sort()
    # 开始生成简易帮助
    simple_help_tuple_dic = {}
    for type_ in types:
        simple_help_tuple_dic[type_] = []
        for i, k in enumerate(sorted(_plugins_data[type_])):
            # 超管禁用flag, True表示禁用
            flag = True
            if plugins_manager.get_plugin_status(k, "all"):
                flag = False
            if group_id:
                flag = flag or not plugins_manager.get_plugin_status(k, "group") \
                       or not group_manager.get_plugin_status(k, group_id, True)
            _post_num = '1' if flag else '0'
            # 群聊禁用
            _pre_num = '0' if group_id and group_manager.get_plugin_status(k, group_id) else '1'
            # (群功能状态|全局禁用状态, 序号.功能名)
            simple_help_tuple_dic[type_].append([_pre_num+_post_num, f"{i+1}.{k}"])
    # 简易帮助图片合成
    random_bk = random.choice(os.listdir(random_bk_path))
    template_path = str(Path(__file__).parent / "templates")
    pic = await template_to_pic(
        template_path=template_path,
        template_name="help.html",
        templates={
            "bk": random_bk,
            "pgs_dic": simple_help_tuple_dic,
        },
        pages={
            "base_url": f"file://{template_path}",
        },
        wait=0,
    )
    Image.open(io.BytesIO(pic)).save(simple_help_image)


def get_plugin_help(msg: str, user_type: int = 0) -> Optional[str]:
    """
    获取功能的帮助信息
    :param msg: 功能cmd
    :param user_type: 标识用户类型，0为一般用户，1为管理员，2为超管
    """
    result = ""
    # 获取普通插件帮助说明
    normal_module = plugins2settings_manager.get_plugin_module(msg)
    if normal_module:
        _plugin = nonebot.plugin.get_plugin(normal_module)
        _module = _plugin.module
        try:
            result = _module.__getattribute__("__plugin_usage__")
        except AttributeError:
            result = ""
            pass
        if user_type == 2:
            try:
                result += "\n{:=^70s}\n".format('超管额外命令') if result else ""
                result += _module.__getattribute__("__plugin_superuser_usage__")
            except AttributeError:
                result += ""
                pass
    # 获取管理插件帮助说明
    if user_type > 0:
        admin_module = admin_manager.get_plugin_module(msg)
        if admin_module:
            _plugin = nonebot.plugin.get_plugin(admin_module)
            _module = _plugin.module
            try:
                result = _module.__getattribute__("__plugin_usage__")
            except AttributeError:
                result = ""
                pass
            if user_type == 2:
                try:
                    result += "\n{:=^70s}\n".format('超管额外命令') if result else ""
                    result += _module.__getattribute__("__plugin_superuser_usage__")
                except AttributeError:
                    result += ""
                    pass
    # 获取超管帮助说明
    if user_type == 2:
        superuser_module = super_manager.get_plugin_module(msg)
        if superuser_module:
            _plugin = nonebot.plugin.get_plugin(superuser_module)
            _module = _plugin.module
            try:
                result = _module.__getattribute__("__plugin_usage__")
            except AttributeError:
                result = ""
                pass
    if result:
        return _get_result_by_usage(result)
    return None


def _get_result_by_usage(usage):
    """
    通过usage获取功能的帮助图片
    :param usage: 帮助信息
    """
    fontname = "SourceHanSansCN-Regular.otf"
    textimg = Text2Image.from_text(
        usage,
        fontsize=24,
        fontname=fontname,
        ischeckchar=False
    ).to_image()
    width, height = textimg.size
    bk = IMG.open(IMAGE_PATH / "background" / "usage.jpg")
    scale = bk.width / bk.height
    width, height = max(int(height * scale), width) * 1.15, max(int(width / scale), height) * 1.2
    bk = bk.resize((int(width), int(height)))
    chara_size = int(0.15*width) if int(0.15*width) < height else height
    w_pos = int(width-0.95*chara_size)
    h_pos = int(height-chara_size)
    chara_bk = IMG.open(IMAGE_PATH / "background" / "knd.png").resize((chara_size, chara_size))
    bk.paste(chara_bk, (w_pos, h_pos), alpha=True)
    bk.paste(textimg, (int(width * 0.05), 0), alpha=True, center_type="by_height")
    return bk.pic2bs4()
