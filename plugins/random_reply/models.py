import time
from utils.utils import scheduler
from nonebot.adapters.onebot.v11 import Message
from dataclasses import dataclass
from typing import Protocol


class UserInfo:
    def __init__(self, qq: int = 0, group: int = 0, text: str = "", state: int = 0, cid: int = 0):
        """
        :param qq: 用户qq号
        :param group: 用户所在群号
        :param text: 用户发送的消息文本
        :param state: 用户响应对话的当前状态
        :param cid: 用户触发的命令cid
        """
        self.qq: int = int(qq)
        self.group: int = int(group)
        self.name: str = ""
        self.nickname: str = ""
        self.level: int = 0
        self.gender: str = ""  # male 或 female 或 unknown
        self.text: str = text
        self.state: int = state  # 多轮对话状态
        self.cid: int = cid


class Func(Protocol):
    async def __call__(self, user: UserInfo, *args, **kwargs) -> (Message, int):
        ...


@dataclass
class Command:
    """
    id: 命令id 为 每一种对话 的唯一标识符，不可重复
    reg: 触发命令的关键字
    func: 每一种对话 对应的 函数逻辑
    need_at: 触发对话是否需要艾特机器人
    priority: 对话响应优先级
    mode: reg->正则匹配器，ntc->通知匹配器，cmd->命令匹配器
    alias: cmd->命令匹配器时，针对命令触发的别名
    next: 标识对话是否有多轮对话的资格
    """
    id: int
    reg: str
    func: Func
    need_at: bool = False
    priority: int = 5
    mode: str = "reg"
    alias: set = None
    next: bool = False


class RetryManager:
    def __init__(self):
        self.data = {}

    def exist(self, qq: int, group: int):
        if self.data.get(f"{qq}_{group}") and self.data[f"{qq}_{group}"]["run"] == True:
            return True
        return False

    def get(self, qq: int, group: int):
        if self.exist(qq, group):
            return self.data[f"{qq}_{group}"]
        return {}

    def add(self, qq: int, group: int, cid: int, state: int):
        if not self.exist(qq, group):
            self.data[f"{qq}_{group}"] = {
                "cid": cid,
                "state": state,
                "cnt": 0,
                "time": time.time(),
                "run": True
            }
        else:
            self.data[f"{qq}_{group}"]["run"] = True
            self.data[f"{qq}_{group}"]["time"] = time.time()
            self.data[f"{qq}_{group}"]["cnt"] = self.data[f"{qq}_{group}"].get("cnt", 0) + 1

    def remove(self, qq: int, group: int):
        if self.exist(qq, group):
            self.data.pop(f"{qq}_{group}")

    def clear_data(self):
        _data = self.data
        for each in _data.copy():
            data = self.data.get(each)
            if data and data['time'] + 30 < time.time():
                self.data.pop(each)


retry_manager = RetryManager()


# 定时清除超时retry名单(会话超过30s无响应)
@scheduler.scheduled_job(
    "interval",
    minutes=1,
    seconds=30
)
async def _():
    retry_manager.clear_data()