import math
from typing import Optional, Dict
from nonebot.adapters.onebot.v11 import MessageEvent
from .data_class import StaticData
from utils.utils import FreqLimiter
from services.log import logger
from pathlib import Path
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


class Plugins2cdManager(StaticData):
    """
    插件命令 cd 管理器
    """
    def __init__(self, file: Path):
        self.file = file
        self._limit_data = {}
        super().__init__(None)
        self._freq_limiter: Dict[str, FreqLimiter] = {}
        self._cd_ban_limiter: Dict[str, FreqLimiter] = {}
        if file.exists():
            with open(file, "r", encoding="utf8") as f:
                self._data = yaml.load(f)
        if "PluginCdLimit" in self._data.keys():
            self._data = (
                self._data["PluginCdLimit"] if self._data["PluginCdLimit"] else {}
            )

    def add_cd_limit(
        self,
        plugin: str,
        *,
        cd: Optional[int] = 5,
        status: Optional[bool] = True,
        check_type: Optional[str] = "all",
        limit_type: Optional[str] = "user",
        rst: Optional[str] = None,
        count_limit: Optional[int] = 1,
        data_dict: Optional[dict] = None,
    ):
        """
        添加插件调用 cd 限制
        :param plugin: 插件模块名称
        :param cd: cd 时长
        :param status: 默认开关状态
        :param check_type: 检查类型 'private'/'group'/'all'，限制私聊/群聊/全部
        :param limit_type: 限制类型 监听对象，以user_id或group_id作为键来限制，'user'：用户id，'group'：群id
        :param rst: 回复的话，为空则不回复
        :param count_limit: cd 时长内命令最多触发的次数
        :param data_dict: 封装好的字典数据
        """
        if data_dict:
            cd = data_dict.get("cd") if data_dict.get("cd") is not None else cd
            status = data_dict.get("status") if data_dict.get("status") is not None else status
            check_type = data_dict.get("check_type") if data_dict.get("check_type") is not None else check_type
            limit_type = data_dict.get("limit_type") if data_dict.get("limit_type") is not None else limit_type
            rst = data_dict.get("rst")
            count_limit = data_dict.get("count_limit") if data_dict.get("count_limit") is not None else count_limit
        if check_type not in ["all", "group", "private"]:
            raise ValueError(
                f"{plugin} 添加cd限制错误，‘check_type‘ 必须为 'private'/'group'/'all'"
            )
        if limit_type not in ["user", "group"]:
            raise ValueError(f"{plugin} 添加cd限制错误，‘limit_type‘ 必须为 'user'/'group'")
        self._data[plugin] = {
            "cd": cd,
            "status": status,
            "check_type": check_type,
            "limit_type": limit_type,
            "rst": rst,
            "count_limit": count_limit,
        }

    def get_plugin_cd_data(self, plugin: str) -> Optional[dict]:
        """
        获取插件cd数据
        :param plugin: 模块名
        """
        if self.check_plugin_cd_status(plugin):
            return self._data[plugin]
        return None

    def check_plugin_cd_status(self, plugin: str) -> bool:
        """
        检测插件是否有 cd
        :param plugin: 模块名
        """
        return (
            plugin in self._data.keys()
            and self._data[plugin]["cd"] > 0
            and self._data[plugin]["status"]
        )

    def remove_cd(self, plugin: str, id_: int):
        """
        解除cd限制
        :param plugin: 模块名
        :param id_: 限制 id
        """
        self._freq_limiter[plugin].remove_cd(id_)

    def check(self, plugin: str, id_: int) -> bool:
        """
        检查 cd(True为cd好了，False为还在cd中)
        :param plugin: 模块名
        :param id_: 限制 id
        """
        return self._freq_limiter[plugin].count_check(id_)

    def get_cd(self, plugin: str, id_: int) -> int:
        """
        返回 cd
        :param plugin: 模块名
        :param id_: 限制 id
        """
        if not self.check(plugin, id_):
            return math.ceil(self._freq_limiter[plugin].left_time(id_))
        return 0

    def get_cd_count(self, plugin: str, id_: int) -> int:
        """
        返回 cd 内使用次数
        :param plugin: 模块名
        :param id_: 限制 id
        """
        return self._freq_limiter[plugin].get_cd_count(id_)

    def sub_cd_count(self, plugin: str, id_: int):
        """
        增加 cd 内使用次数
        :param plugin: 模块名
        :param id_: 限制 id
        """
        self._freq_limiter[plugin].sub_cd_count(id_)

    def start_cd(self, plugin: str, id_: int, cd: int = 0, cd_count: int = 1):
        """
        开始cd
        :param plugin: 模块名
        :param id_: cd 限制类型
        :param cd: cd 时长
        :param cd_count: cd 次数
        :return:
        """
        if self._freq_limiter.get(plugin):
            self._freq_limiter[plugin].start_cd(id_, cd, cd_count)

    def reload_cd_limit(self):
        """
        加载 cd 限制器
        :return:
        """
        for plugin in self._data:
            if self.check_plugin_cd_status(plugin):
                self._freq_limiter[plugin] = FreqLimiter(
                    self.get_plugin_cd_data(plugin)["cd"],
                    self.get_plugin_cd_data(plugin)["count_limit"]
                    if self.get_plugin_cd_data(plugin).get("count_limit") else 1
                )
                self._cd_ban_limiter[plugin] = FreqLimiter(self.get_plugin_cd_data(plugin)["cd"], 3)
        logger.info(f"已成功加载 {len(self._freq_limiter)} 个Cd限制.")

    def reload(self):
        """
        重载本地数据
        """
        if self.file.exists():
            with open(self.file, "r", encoding="utf8") as f:
                self._data: dict = yaml.load(f)
                self._data = self._data["PluginCdLimit"]
                self.reload_cd_limit()

    def get_plugin_data(self, plugin: str) -> dict:
        """
        获取单个模块限制数据
        :param plugin: 模块名
        """
        if self._data.get(plugin) is not None:
            return self._data.get(plugin)
        return {}

    # 以下为恶意刷cd检测
    # 以下为恶意刷cd检测
    # 以下为恶意刷cd检测
    def remove_cd_ban(self, plugin: str, id_: int):
        """
        解除用cd刷屏名单
        :param plugin: 模块名
        :param id_: 限制 id
        """
        self._cd_ban_limiter[plugin].remove_cd(id_)

    def add_cd_ban(self, plugin: str, id_: int):
        """
        添加用cd刷屏名单
        :param plugin: 模块名
        :param id_: 限制 id
        """
        self._cd_ban_limiter[plugin].start_cd(id_)

    def check_cd_ban(self, plugin: str, id_: int):
        """
        检测用cd刷屏名单
        :param plugin: 模块名
        :param id_: 限制 id
        """
        return self._cd_ban_limiter[plugin].count_check(id_)

    def isexist_cd_ban(self, plugin: str, id_: int):
        """
        获取已用cd刷屏次数
        :param plugin: 模块名
        :param id_: 限制 id
        """
        return self._cd_ban_limiter[plugin].count.isexist(id_)

    def get_cd_ban_count(self, plugin: str, id_: int):
        """
        获取已用cd刷屏次数
        :param plugin: 模块名
        :param id_: 限制 id
        """
        return self._cd_ban_limiter[plugin].get_cd_count(id_)

    def get_cd_ban_maxcount(self, plugin: str):
        """
        获取cd刷屏最大次数限制
        :param plugin: 模块名
        """
        return self._cd_ban_limiter[plugin].count.max_count

    def set_flag(self, module: str, event: MessageEvent, flag: bool = True, num: int = 1):
        """
        设置与一个事件相关的确认进入cd的标志
        """
        self._limit_data[module] = {event.message_id: (flag, num)}

    def get_flag(self, module: str, event: MessageEvent):
        """
        获取与一个事件相关的确认进入cd的标志，次数
        """
        try:
            return self._limit_data[module].pop(event.message_id)
        except:
            return False, 0