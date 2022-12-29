import nonebot
from pathlib import Path
from ruamel import yaml
from ruamel.yaml import round_trip_load, round_trip_dump, YAML
from services.log import logger
from models.group_info import GroupInfo
from utils.utils import get_matchers
from manager import plugins2settings_manager, admin_manager, super_manager, group_manager


_yaml = YAML(typ="safe")


async def init_plugins_settings(data_path: Path):
    """
    初始化插件设置，从插件中获取 __plugin_name__，__plugin_settings__
    """
    plugins2settings_file = data_path / "configs" / "plugins2settings.yaml"
    plugins2settings_file.parent.mkdir(exist_ok=True, parents=True)
    _tmp_module = {}  # 存放plugins2settings_manager的旧数据
    _tmp = []  # 存放现有响应器对应的所有插件名
    # 读取旧数据
    for x in plugins2settings_manager.keys():
        try:
            _plugin = nonebot.plugin.get_plugin(x)
            _module = _plugin.module
            plugin_name = _module.__getattribute__("__plugin_name__")
            _tmp_module[x] = plugin_name
        except (KeyError, AttributeError) as e:
            logger.warning(f"配置文件 模块：{x} 获取 plugin_name 失败...{e}")
            _tmp_module[x] = ""
    # 读取完旧数据，读取现在的新数据
    for matcher in get_matchers():
        if matcher.plugin_name in _tmp:
            continue
        _tmp.append(matcher.plugin_name)
        if matcher.plugin_name not in plugins2settings_manager.keys():
            _plugin = nonebot.plugin.get_plugin(matcher.plugin_name)
            try:
                _module = _plugin.module
            except AttributeError:
                logger.warning(f"插件 {matcher.plugin_name} 加载失败...，插件控制未加载.")
            else:
                try:
                    plugin_name = _module.__getattribute__("__plugin_name__")
                    # 加载管理插件
                    if "[admin]" in plugin_name.lower():
                        plg_name = plugin_name.lower().replace("[admin]", "").strip()
                        try:
                            admin_settings = _module.__getattribute__(
                                "__plugin_settings__"
                            )
                            level = admin_settings["admin_level"]
                            cmd = admin_settings.get("cmd")
                        except (AttributeError, KeyError):
                            level = 5
                            cmd = []
                        cmd = cmd if cmd is not None else []
                        level = level if level is not None else 5
                        for i in plg_name.split('/'):
                            if i not in cmd:
                                cmd.append(i)
                        admin_manager.add_admin_plugin_settings(
                            matcher.plugin_name, cmd, level
                        )
                        continue
                    # 加载超管插件
                    elif "[superuser]" in plugin_name.lower():
                        plg_name = plugin_name.lower().replace("[superuser]", "").strip()
                        try:
                            super_settings = _module.__getattribute__(
                                "__plugin_settings__"
                            )
                            cmd = super_settings.get("cmd")
                        except (AttributeError, KeyError):
                            cmd = []
                        cmd = cmd if cmd is not None else []
                        for i in plg_name.split('/'):
                            if i not in cmd:
                                cmd.append(i)
                        super_manager.add_super_plugin_settings(
                            matcher.plugin_name, cmd
                        )
                        continue
                    # 跳过被动插件
                    elif "[hidden]" in plugin_name.lower():
                        continue
                except AttributeError:
                    pass
                # 加载通用插件
                else:
                    try:
                        _tmp_module[matcher.plugin_name] = plugin_name
                        plugin_settings = _module.__getattribute__(
                            "__plugin_settings__"
                        )
                        plugin_settings["cmd"] = plugin_settings.get("cmd", [])
                    except AttributeError:
                        logger.warning(f"插件 {matcher.plugin_name} 加载失败...，插件控制未加载.")
                        continue
                    # 将插件名加入cmd列表中
                    for i in plugin_name.split('/'):
                        if i not in plugin_settings["cmd"]:
                            plugin_settings["cmd"].append(i)
                    try:
                        plugin_type = _module.__getattribute__("__plugin_type__")
                    except AttributeError:
                        plugin_type = "娱乐功能"
                    # 将插件类型加入cmd列表中
                    for i in plugin_type.split('&'):
                        if i not in plugin_settings["cmd"]:
                            plugin_settings["cmd"].append(i)
                    # 添加新插件数据
                    if plugin_settings:
                        plugins2settings_manager.add_plugin_settings(
                            matcher.plugin_name,
                            plugin_type=plugin_type,
                            **plugin_settings,
                        )
                        # 若新插件默认为关闭状态，立即刷新已有的所有群组的插件状态
                        if not plugin_settings.get('default_status', True):
                            groups = await GroupInfo.get_all_group()
                            for group in groups:
                                group_manager.block_plugin(matcher.plugin_name, int(group.group_id))

    _tmp_data = {"PluginSettings": plugins2settings_manager.get_data()}
    # 写入新数据
    with open(plugins2settings_file, "w", encoding="utf8") as wf:
        yaml.dump(_tmp_data, wf, Dumper=yaml.RoundTripDumper, allow_unicode=True)
    # 设置插件文件说明
    _data = round_trip_load(open(plugins2settings_file, encoding="utf8"))
    _data["PluginSettings"].yaml_set_start_comment(
        """# 模块与对应命令和对应群权限
# 用于生成帮助图片 和 开关功能
# key：模块名称
# level：需要的群等级
# default_status：加入群时功能的默认开关状态
# limit_superuser: 功能状态是否限制超级用户
# cmd: 关闭[cmd] 都会触发命令 关闭对应功能，cmd列表第一个词为统计的功能名称
# plugin_type: 帮助类别 示例：'烧烤相关' """,
        indent=2,
    )
    for plugin in _data["PluginSettings"].keys():
        _data["PluginSettings"][plugin].yaml_set_start_comment(
            f"{plugin}：{_tmp_module[plugin]}", indent=2
        )
    with open(plugins2settings_file, "w", encoding="utf8") as wf:
        round_trip_dump(_data, wf, Dumper=yaml.RoundTripDumper, allow_unicode=True)
    logger.info(f"已成功加载 {len(plugins2settings_manager.get_data())} 个非限制插件.")
