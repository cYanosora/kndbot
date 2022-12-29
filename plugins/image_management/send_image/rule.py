from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.typing import T_State, T_RuleChecker
from utils.utils import get_message_text, is_number
from manager import Config
try:
    from plugins.image_management.pjsk_images.pjsk_image import pjsk_findin_db
    pjsk_flag = True
except ModuleNotFoundError:
    pjsk_flag = False


def rule() -> T_RuleChecker:
    """
    检测文本是否在图库列表中
    """
    async def check_rule(event: GroupMessageEvent, state: T_State) -> bool:
        msg = get_message_text(event.json()).strip()
        pic_cmd_head_list = ["看", "来点", "来丶"]
        for x in pic_cmd_head_list:
            if msg.startswith(x):
                # 获取CommandArg
                msg = msg[len(x):].strip()
                gallery = ""
                ids = []
                raw_ids = []

                # 排除特殊词汇
                for each in Config.get_config("pjsk_alias", "BANWORDS"):
                    if msg.startswith(each.split("_")[0]):
                        gallery = msg
                        raw_ids = msg[len(each):].strip().replace(',', ' ').replace('，', ' ').split()
                        break

                # 搜索默认公开图库
                if not gallery:
                    for each in Config.get_config("image_management", "IMAGE_DIR_LIST"):
                        if msg.startswith(each):
                            gallery = each
                            raw_ids = msg[len(each):].strip().replace(',', ' ').replace('，', ' ').split()
                            break

                # 搜索烧烤图库
                if not gallery:
                    gallery, raw_ids = await pjsk_findin_db(msg, event.group_id)
                if not gallery:
                    return False

                # 可能是符合规则的数字串，也可能是非数字
                if raw_ids:
                    final_ids = set()
                    for unsolved_ids in raw_ids:
                        if '-' in unsolved_ids:
                            start, end = unsolved_ids.split('-')
                            if is_number(start) and is_number(end) and int(end) >= int(start):
                                true_start = int(start) if int(start) > 0 else 1
                                true_end = int(end) + 1 if int(end) - int(start) < 99 else true_start + 25
                                for num in range(true_start, true_end):
                                    final_ids.add(num)
                        elif is_number(unsolved_ids):
                            final_ids.add(int(unsolved_ids))
                    final_ids = list(final_ids)
                    final_ids.sort()
                    ids = final_ids
                    # raw_ids无法转为ids，说明raw_ids是非数字
                    if not ids:
                        return False
                state['sendpic_name'] = gallery
                state['sendpic_imgid'] = ids
                return True
        return False
    return check_rule