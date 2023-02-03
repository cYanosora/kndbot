from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.permission import GROUP
from utils.data_utils import init_rank
from models.bag_user import BagUser
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image, reply
from utils.utils import is_number

__plugin_name__ = "我的金币"
__plugin_type__ = "商店"
__plugin_usage__ = """
usage：
    查看金币
    指令：
        我的金币
        金币排行
""".strip()
__plugin_settings__ = {
    "cmd": ["我的金币", "商店"],
}


my_gold = on_command("我的金币", priority=5, block=True, permission=GROUP)

gold_rank = on_command("金币排行", priority=5, block=True, permission=GROUP)


@my_gold.handle()
async def _(event: GroupMessageEvent):
    msg = await BagUser.get_user_total_gold(event.user_id, event.group_id)
    await my_gold.send(
        image(b64=pic2b64(text2image(msg))),
        at_sender=True
    )


@gold_rank.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    num = arg.extract_plain_text().strip()
    await gold_rank.send("请稍等..正在整理数据...")
    if is_number(num) and 51 > int(num) > 10:
        num = int(num)
    else:
        num = 10
    all_users = await BagUser.get_all_users(event.group_id)
    all_user_id = [user.user_qq for user in all_users]
    all_user_data = [user.gold for user in all_users]
    rank_image = await init_rank(
        "金币排行", all_user_id, all_user_data, event.group_id,
        num, 50, f"g{event.group_id}_{num}_goldrank"
    )
    if rank_image:
        await gold_rank.finish(reply(event.message_id)+image(b64=rank_image.pic2bs4()))
