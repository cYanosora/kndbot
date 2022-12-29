import copy
import time
from pathlib import Path
from .configs_manager import Config
from manager import StaticData
try:
    import ujson as json
except:
    import json


class Mute:
    def __init__(self):
        # key: 群号_qq号
        # value: {data:list,max_count:int,next_time:float}
        self.data = {}

    def check(self, key: str) -> bool:
        return time.time() >= self.data[key]["next_time"]

    def append(self, key: str, content: str, cd_time: float, type: str) -> bool:
        """
        :param key: 群号_qq号
        :param content: 说过的话
        :param cd_time: 限制的时间范围
        :param type: 禁言类型，allmute/mute/cmdmute
        """
        if type not in ['mute', 'allmute', 'cmdmute']:
            return False
        self._create(key, cd_time)
        # 刷屏行为不被计入则不添加
        if not self.get_flag(key):
            self.set_flag(key, True)
            return False
        # 到了新时间限定范围，刷新
        if self.check(key):
            self.data[key]["next_time"] = time.time() + cd_time
            self.data[key]["data"] = [content]
            self.data[key]["max_count"] = 1
        else:
            self.data[key]["data"].append(content)
            # 单条消息处理禁言
            if type == 'mute':
                new_count = max(self.data[key]["max_count"], self.data[key]["data"].count(content))
                self.data[key]["max_count"] = new_count
            # 全部消息处理禁言
            else:
                self.data[key]["max_count"] = len(self.data[key]["data"])
        return True

    def clear(self, key: str):
        if self.data.get(key):
            self.data.pop(key)

    def clear_data(self):
        data = copy.deepcopy(self.data)
        for key in data:
            if (
                self.data.get(key)
                and time.time() >= self.data[key]["next_time"]
                and self.data[key]["max_count"] == 0
            ):
                self.data.pop(key)

    def check_count(self, key: str, limit_max_count: int) -> bool:
        """
        :param key: 群号_qq号
        :param limit_max_count: 限制次数
        """
        # 若 没有key 或 key对应的限制时段进入新时段区间 或 限制时段内发言次数未耗尽
        if (
            self.data.get(key) is None or
            self.check(key) or
            self.data[key]["max_count"] < limit_max_count
        ):
            return True
        else:
            return False

    def _create(self, key: str, limit_time: float):
        if self.data.get(key) is None:
            self.data[key] = {"max_count": 0, "next_time": time.time() + limit_time, "data": [], "flag": True}

    def set_flag(self, key: str, flag: bool = True):
        """
        设置 key此次 刷屏行为 是否被记入，默认计入
        """
        self._create(key, 0)
        self.data[key]["flag"] = flag

    def get_flag(self, key: str) -> bool:
        """
        获取 key当前 刷屏行为 是否被记入，默认计入
        """
        return self.data[key].get("flag", True)


class MuteDataManager(StaticData):
    """
    刷屏禁言功能 群数据记录器
    """

    def __init__(self, file: Path):
        self.file = file
        super().__init__(None)
        if file.exists():
            with open(file, "r", encoding="utf8") as f:
                self._data: dict = json.load(f)

    def _save_data(self):
        with open(self.file, "w", encoding="utf8") as f:
            json.dump(self._data, f, indent=4)

    def get_group_mute_settings(self, group_id: str):
        if not self._data.get(group_id):
            self._data[group_id] = {
                "count": Config.get_config("mute", "MUTE_DEFAULT_COUNT"),
                "time": Config.get_config("mute", "MUTE_DEFAULT_TIME"),
                "duration": Config.get_config("mute", "MUTE_DEFAULT_DURATION"),
                "type": Config.get_config("mute", "MUTE_DEFAULT_TYPE")
            }
        else:
            for i in ['count', 'time', 'duration', 'type']:
                if i not in self._data[group_id]:
                    self._data[group_id][i] = Config.get_config("mute", f"MUTE_DAFAULT_{i.upper()}")
        self._save_data()
        return self._data[group_id]

    def set_group_mute_settings(
        self,
        group_id: str,
        **kwargs
    ):
        self.get_group_mute_settings(group_id)
        for arg in kwargs:
            self._data[group_id][f"{arg}"] = kwargs[arg]
        self._save_data()

