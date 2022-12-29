from pathlib import Path
from ruamel.yaml import YAML
from typing import List, Optional, Union
from .data_class import StaticData

yaml = YAML(typ="safe")


class Plugins2settingsManager(StaticData):
    """
    插件命令阻塞 管理器
    """

    def __init__(self, file: Path):
        self.file = file
        super().__init__(None)
        if file.exists():
            with open(file, "r", encoding="utf8") as f:
                self._data = yaml.load(f)
        if self._data:
            if "PluginSettings" in self._data.keys():
                self._data = (
                    self._data["PluginSettings"] if self._data["PluginSettings"] else {}
                )

    def add_plugin_settings(
        self,
        plugin: str,
        cmd: Optional[List[str]] = None,
        default_status: Optional[bool] = True,
        level: Optional[int] = 5,
        plugin_type: str = "功能",
        **kwargs
    ):
        """
        添加一个插件设置
        :param plugin: 插件模块名称
        :param cmd: 命令 或 命令别名
        :param default_status: 默认开关状态
        :param level: 使用功能所需的群权限等级
        :param plugin_type: 插件类型
        """
        if kwargs:
            cmd = kwargs.get("cmd") if kwargs.get("cmd") is not None else []
            default_status = (
                kwargs.get("default_status")
                if kwargs.get("default_status") is not None
                else default_status
            )
            level = kwargs.get("level") if kwargs.get("level") is not None else level
            plugin_type = (
                kwargs.get("plugin_type")
                if kwargs.get("plugin_type") is not None
                else plugin_type
            )
        self._data[plugin] = {
            "level": level,
            "default_status": default_status,
            "cmd": cmd,
            "plugin_type": plugin_type
        }

    def get_plugin_data(self, module: str) -> dict:
        """
        通过模块名获取数据
        :param module: 模块名称
        """
        if self._data.get(module) is not None:
            return self._data.get(module)
        return {}

    def get_plugin_module(
        self, cmd: str, is_all: bool = False
    ) -> Union[str, List[str]]:
        """
        根据 cmd 获取功能 modules
        :param cmd: 命令
        :param is_all: 获取全部包含cmd的模块
        """
        keys = []
        for key in self._data.keys():
            if cmd in self._data[key]["cmd"]:
                if is_all:
                    keys.append(key)
                else:
                    return key
        return keys

    def reload(self):
        """
        重载本地数据
        """
        if self.file.exists():
            with open(self.file, "r", encoding="utf8") as f:
                self._data: dict = yaml.load(f)
                self._data = self._data["PluginSettings"]
