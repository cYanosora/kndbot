import os
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message
import random
from pathlib import Path
from typing import Optional, Union, Tuple
from enum import Enum
from configs.config import NICKNAME
from ._config import config
try:
    import ujson as json
except ModuleNotFoundError:
    import json


class Meals(Enum):
    BREAKFAST   = "breakfast"
    LUNCH       = "lunch"
    SNACK       = "snack"
    DINNER      = "dinner"
    MIDNIGHT    = "midnight"


class EatingManager:
    def __init__(self, path: Optional[Path]):
        self._data = {}
        if not path:
            data_file = Path() / "data.json"
        else:
            data_file = path / "data.json"
        
        self.data_file = data_file
        if not data_file.exists():
            with open(data_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(dict()))
                f.close()

        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)

        self._init_json()

    def _init_json(self) -> None:
        if "basic_food" not in self._data.keys():
            self._data["basic_food"] = []
        if "group_food" not in self._data.keys():
            self._data["group_food"] = {}
        if "eating" not in self._data.keys():
            self._data["eating"] = {}
        if "knd_food" not in self._data.keys():
            self._data["knd_food"] = []
    
    def _init_data(self, group_id: str, user_id: str) -> None:
        """
        初始化用户信息
        """
        if group_id not in self._data["group_food"].keys():
            self._data["group_food"][group_id] = []
        if group_id not in self._data["eating"].keys():
            self._data["eating"][group_id] = {}
        if user_id not in self._data["eating"][group_id].keys():
            self._data["eating"][group_id][user_id] = 0

    def get2eat(self, event: GroupMessageEvent) -> Tuple[Union[Message, str], bool]:
        """
        今天吃什么
        """
        user_id = str(event.user_id)
        group_id = str(event.group_id)

        self._init_data(group_id, user_id)
        if not self.eating_check(event):
            return random.choice(
                [
                    "你今天已经吃得够多了吧>n<",
                    "...吃这么多的吗？",
                    "你怎么还吃啊？你不工作的吗？"
                ]
            ), False
        else:
            # 菜单全为空，建议避免["basic_food"]为空
            if len(self._data["basic_food"]) == 0 \
            and len(self._data["group_food"][group_id]) == 0\
            and len(self._data["knd_food"]) == 0:
                return "还没有菜单呢，就先饿着肚子吧，请[添加 菜名]", False
            flag = False
            rd = random.random()
            if rd < 0.65:
                food_list = self._data["basic_food"].copy()
                if len(self._data["group_food"][group_id]) > 0:
                    food_list.extend(self._data["group_food"][group_id])
                msg = f"{NICKNAME}建议[user]吃{random.choice(food_list)}呢"
            elif rd < 0.95:
                food_list = self._data["knd_food"].copy()
                msg = f"建议[user]和{NICKNAME}一起吃{random.choice(food_list)}呢OvO"
                flag = True if random.random() < 0.25 else False
            else:
                msg = f"{NICKNAME}觉得[user]应该去吃啤酒烧烤呢~(。>︿<)"
            self._data["eating"][group_id][user_id] += 1
            self.save()
            return msg, flag

    def food_exists(self, _food_: str) -> int:
        """
        检查菜品是否存在
        1:  存在于基础菜单
        2:  存在于群菜单
        3:  存在于杯面菜单
        0:  不存在
        """
        for food in self._data["basic_food"]:
            if food == _food_:
                return 1

        for group_id in self._data["group_food"]:
            for food in self._data["group_food"][group_id]:
                if food == _food_:
                    return 2
        for food in self._data["knd_food"]:
            if food == _food_:
                return 3
        return 0

    def eating_check(self, event: GroupMessageEvent) -> bool:
        """
        检查是否吃饱
        """
        user_id = str(event.user_id)
        group_id = str(event.group_id)
        return False if self._data["eating"][group_id][user_id] >= config["eating_limit"] else True

    def add_group_food(self, new_food: str, event: GroupMessageEvent) -> str:
        """
        添加至群菜单中 GROUP_ADMIN | GROUP_OWNER 权限
        """
        user_id = str(event.user_id)
        group_id = str(event.group_id)

        self._init_data(group_id, user_id)
        status = self.food_exists(new_food)
        if status == 1:
            return f"{new_food} 已在基础菜单中~"
        elif status == 2:
            return f"{new_food} 已在群特色菜单中~"

        self._data["group_food"][group_id].append(new_food)
        self.save()
        return f"{new_food} 已加入群特色菜单~"

    def add_basic_food(self, new_food: str) -> str:
        """
        添加至基础菜单 SUPERUSER 权限
        """
        status = self.food_exists(new_food)
        if status == 1:
            return f"{new_food} 已在基础菜单中~"
        elif status == 2:
            return f"{new_food} 已在群特色菜单中~"

        self._data["basic_food"].append(new_food)
        self.save()
        return f"{new_food} 已加入基础菜单~"

    def remove_food(self, food_to_remove: str, event: GroupMessageEvent) -> str:
        """
        从基础菜单移除 SUPERUSER 权限
        从群菜单中移除 GROUP_ADMIN | GROUP_OWNER 权限
        """
        user_id = str(event.user_id)
        group_id = str(event.group_id)
        
        self._init_data(group_id, user_id)
        status = self.food_exists(food_to_remove)
        if not status:
            return f"{food_to_remove} 不在菜单中哦~"

        # 在群菜单
        if status == 2:
            self._data["group_food"][group_id].remove(food_to_remove)
            self.save()
            return f"{food_to_remove} 已从群菜单中删除~"
        # 在基础菜单或杯面菜单
        else:
            if user_id not in config["superusers"]:
                return f"{food_to_remove} 在基础菜单中，非超管不可操作哦~"
            else:
                _type = "basic_food" if status == 1 else "knd_food"
                self._data[_type].remove(food_to_remove)
                self.save()
                return f"{food_to_remove} 已从基础菜单中删除~"

    def reset_eating(self) -> None:
        """
        重置三餐 eating times
        """
        for group_id in self._data["eating"].keys():
            for user_id in self._data["eating"][group_id].keys():
                self._data["eating"][group_id][user_id] = 0
        self.save()

    def save(self) -> None:
        """
        保存数据
        """
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=4)

    def show_group_menu(self, event: GroupMessageEvent) -> str:
        user_id = str(event.user_id)
        group_id = str(event.group_id)
        msg = []
        
        self._init_data(group_id, user_id)
        if len(self._data["group_food"][group_id]) > 0:
            msg += MessageSegment.text("---群特色菜单---\n")
            for food in self._data["group_food"][group_id]:
                msg += MessageSegment.text(f"{food}\n")
        
        return msg if len(msg) > 0 else "还没有群特色菜单呢，请[添加 菜名]~"


if config.get("what2eat_path"):
    path = Path(config["what2eat_path"])
else:
    path = Path(os.path.join(os.path.dirname(__file__), "resource"))
eating_manager = EatingManager(path)