from collections import deque
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
)
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from .config import config
from .data import setting


def create_matcher(
    command: Union[str, List[str]],
    only_to_me: bool = True,
    private: bool = True,
    priority: int = 5,
    block: bool = True,
) -> Type[Matcher]:
    """
    创建响应器
    """
    params: Dict[str, Any] = {
        "priority": priority,
        "block": block,
    }
    if command:
        on_matcher = on_command
        command = [command] if isinstance(command, str) else command
        params["cmd"] = command.pop(0)
        params["aliases"] = set(command)
    else:
        on_matcher = on_message
    if only_to_me:
        params["rule"] = to_me()
    if not private:
        params["permission"] = GROUP
    return on_matcher(**params)


class Session(dict):
    """ 所有群/用户的会话信息字典 """
    def __init__(self, scope: Literal["private", "public"]) -> None:
        super().__init__()
        self.is_private = scope == "private"

    def __getitem__(self, event: MessageEvent) -> Dict[str, Any]:
        return super().__getitem__(self.id(event))

    def __setitem__(
        self,
        event: MessageEvent,
        value: Union[Tuple[Optional[str], Optional[str]], Dict[str, Any]],
    ) -> None:
        if isinstance(value, tuple):
            conversation_id, parent_id = value
        else:
            conversation_id = value["conversation_id"]
            parent_id = value["parent_id"]
        if self[event]:
            if isinstance(value, tuple):
                self[event]["conversation_id"].append(conversation_id)
                self[event]["parent_id"].append(parent_id)
        else:
            super().__setitem__(
                self.id(event),
                {
                    "conversation_id": deque(
                        [conversation_id], maxlen=config.chatgpt_max_rollback
                    ),
                    "parent_id": deque([parent_id], maxlen=config.chatgpt_max_rollback),
                },
            )

    def __delitem__(self, event: MessageEvent) -> None:
        sid = self.id(event)
        if sid in self:
            super().__delitem__(sid)

    def __missing__(self, _) -> Dict[str, Any]:
        return {}

    def id(self, event: MessageEvent) -> str:
        """会话id的key，即msg.session_id"""
        if self.is_private:
            return event.get_session_id()
        return str(
            event.group_id if isinstance(event, GroupMessageEvent) else event.user_id
        )

    def save(self, name: str, event: MessageEvent) -> None:
        """保存当前群/用户的会话记录，name为会话名称"""
        sid = self.id(event)
        if setting.session.get(sid) is None:
            setting.session[sid] = {}
        setting.session[sid][name] = {
            "conversation_id": self[event]["conversation_id"][-1],
            "parent_id": self[event]["parent_id"][-1],
        }
        setting.save()

    def find(self, event: MessageEvent) -> Dict[str, Any]:
        """获取当前群/用户的会话记录"""
        sid = self.id(event)
        return setting.session[sid]

    def count(self, event: MessageEvent) -> int:
        """获取当前群/用户的对话条数"""
        return len(self[event]["conversation_id"])

    def pop(self, event: MessageEvent) -> Tuple[str, str]:
        """删除当前群/用户最近的对话"""
        conversation_id = self[event]["conversation_id"].pop()
        parent_id = self[event]["parent_id"].pop()
        return conversation_id, parent_id
