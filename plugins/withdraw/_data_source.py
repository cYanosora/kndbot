from nonebot.adapters.onebot.v11 import Message, MessageSegment
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from ._models import WithdrawBase
from typing import Optional, Tuple, Union, List, Any
from utils.utils import is_number
import nonebot

driver = nonebot.get_driver()


async def _get_entry_str(id_: Union[str, int], group_id: Optional[int] = None) -> Tuple[str, bool]:
    """
    说明:
        通过id获取问题字符串
    参数:
        :param id_: 下标
        :param group_id: 群号
    """
    all_entry = await WithdrawBase.get_group_all_entry(group_id)
    if id_.startswith("id:"):
        id_ = id_.split(":")[-1]
    if not is_number(id_) or int(id_) < 0 or int(id_) >= len(all_entry):
        return "id必须为数字且在范围内", False
    return all_entry[int(id_)][0], True


async def delete_word(entry: str, group_id: Optional[int] = None) -> str:
    """
    说明:
        删除群词条
    参数:
        :param entry: 参数
        :param group_id: 群号
    """
    # 输入的是问题的id时
    if entry.startswith("id:"):
        entry, code = await _get_entry_str(entry, group_id)
        # id错误时
        if not code:
            return "指定词条的id必须为数字且在范围内"
    await WithdrawBase.delete_group_entry(entry, group_id)
    return "删除词条成功"


async def show_word(
    group_id: Optional[int],
) -> Union[str, List[Union[str, Message, MessageSegment]]]:
    """
    说明:
        显示词条
    参数:
        :param group_id: 指定的群号，用于群聊
    """
    _problem_list = await WithdrawBase.get_group_all_entry(group_id)
    if not _problem_list:
        return "未收录任何词条.."
    # 组装回复的消息
    return await _build_message(_problem_list)


# 用于将需要回复的问题列表组装为消息段
async def _build_message(
        _problem_list: List[Tuple[Any, Union[Message, MessageSegment, str]]]
) -> List[Union[Message, MessageSegment, str]]:
    index = 0
    str_temp_list = []
    msg_list = []
    temp_str = ""
    for _, problem in _problem_list:
        # 限制单张图片最多显示50张图片
        if len(temp_str.split("\n")) > 50:
            msg_list.append(image(b64=pic2b64(text2image(temp_str, bg_color="#f9f6f2"))))
            temp_str = ""
        if isinstance(problem, str):
            if problem not in str_temp_list:
                str_temp_list.append(problem)
                temp_str += f"{index}. {problem}\n"
        # 问题中含有CQ码
        else:
            # 提前处理之前的词条
            if temp_str:
                msg_list.append(image(b64=pic2b64(text2image(temp_str, bg_color="#f9f6f2"))))
                temp_str = ""
            msg_list.append(f"{index}." + problem)
        index += 1
    # 最后处理剩下的词条
    if temp_str:
        msg_list.append(image(b64=pic2b64(text2image(temp_str, bg_color="#f9f6f2"))))
    return msg_list
