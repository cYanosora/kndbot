import re
from typing import Dict, Any
from nonebot.exception import MockApiException
from nonebot.adapters.onebot.v11 import Bot, Message
from manager import group_manager


# task被动插件发送消息前的预处理
@Bot.on_calling_api
async def handle_api_call(bot: Bot, api: str, data: Dict[str, Any]):
    r = None
    try:
        if (
            (
                (api == "send_msg" and data["message_type"] == "group")
                or api == "send_group_msg"
            )
            and (
                (
                    r := re.search(
                        "^\[\[_task\|(.*)]]",
                        data["message"].strip()
                        if isinstance(data["message"], str)
                        else str(data["message"]["text"]).strip(),
                    )
                )
                or (
                    r := re.search(
                        "^&#91;&#91;_task\|(.*)&#93;&#93;",
                        data["message"].strip()
                        if isinstance(data["message"], str)
                        else str(data["message"]["text"]).strip(),
                    )
                )
            )
            and r.group(1) in group_manager.get_task_data().keys()
        ):
            task = r.group(1)
            group_id = data["group_id"]
            if group_manager.get_group_level(
                group_id
            ) < 0 or not await group_manager.check_group_task_status(group_id, task):
                raise MockApiException(f"被动技能 {task} 处于关闭状态...")
            else:
                msg = str(data["message"]).strip()
                msg = msg.replace(f"&#91;&#91;_task|{task}&#93;&#93;", "").replace(
                    f"[[_task|{task}]]", ""
                )
                data["message"] = Message(msg)
    except TypeError:
        pass
