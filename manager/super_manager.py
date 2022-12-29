from .data_class import StaticData
from typing import List, Optional


class SuperManager(StaticData):
    """
    超管命令 管理器
    """

    def __init__(self):
        super().__init__(None)

    def add_super_plugin_settings(self, plugin: str, cmd: List[str]):
        """
        添加一个超管命令
        :param plugin: 模块
        :param cmd: 别名
        """
        self._data[plugin] = {
            "cmd": cmd,
        }

    def remove_super_plugin_settings(self, plugin: str):
        """
        删除一个管理员命令
        :param plugin: 模块名
        """
        if plugin in self._data.keys():
            del self._data[plugin]

    def get_plugin_module(self, cmd: str) -> Optional[str]:
        """
        根据 cmd 获取功能 modules
        :param cmd: 命令
        """
        for key in self._data.keys():
            if self._data[key].get("cmd") and cmd in self._data[key]["cmd"]:
                return key
        return None
