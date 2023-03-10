from nonebot import on_command
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from models.level_user import LevelUser
from utils.imageutils import text2image, pic2b64
from manager import group_manager, plugins2settings_manager, plugins_manager
from utils.message_builder import image

__plugin_name__ = "群权限查看"
__plugin_type__ = "其他"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    群权限查看
    指令：
        查看群权限       : 查询本群对bot的功能使用权限
        我的权限        : 查询自己对bot的功能管理权限
""".strip()
__plugin_settings__ = {
    "cmd": ["群权限查看", "查看权限"],
}
__plugin_superuser_usage__ = """
superuser_usage
    群权限查看，由超管使用
    指令：
        查看群权限/查看群状态  [群号]   : 查询群功能使用权限
"""

my_level = on_command("我的权限", permission=GROUP, priority=5, block=True)
my_group_level = on_command(
    "查看群权限", aliases={"群权限查看", "查看群状态", "群状态查看"},
    priority=5, permission=GROUP | SUPERUSER, block=True
)


@my_level.handle()
async def _(event: GroupMessageEvent):
    if (level := await LevelUser.get_user_level(event.user_id, event.group_id)) == -1:
        await my_level.finish("您目前没有任何权限，硬要说的话你就是0呢(・ε・；)", at_sender=True)
    await my_level.finish(f"您目前的权限等级：{level}", at_sender=True)


@my_group_level.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if msg.isdigit() and str(event.user_id) in bot.config.superusers:
        group_id = int(msg)
    elif hasattr(event, 'group_id'):
        group_id = event.group_id
    else:
        await my_group_level.finish("没有提供群号！")
        return
    level = group_manager.get_group_level(group_id)
    tmp = ""
    data = plugins2settings_manager.get_data()
    for module in data.keys():
        block_type = ""
        if data[module]["level"] > level:
            block_type = "(群权限不足)"
        elif not group_manager.get_plugin_status(module, group_id):
            block_type = "(群管禁用)"
        elif(
            not group_manager.get_plugin_status(module, group_id, True) or
            not plugins_manager.get_plugin_status(module, block_type="group") or
            not plugins_manager.get_plugin_status(module, block_type="all")
        ):
            block_type = "(master禁用)"
        if block_type:
            tmp += data[module]["cmd"][0] + block_type + '\n'

    task_data = group_manager.get_task_data()
    for task in task_data.keys():
        if not group_manager.check_group_task_status(group_id, task):
            tmp += task_data[task] + '(群管禁用)\n'
    if tmp:
        tmp = "\n目前无法使用的功能：\n" + tmp
        img_flag = True
    else:
        tmp = "\n目前所有功能均可使用"
        img_flag = False
    reply = f"当前群权限：{level}{tmp}"
    if img_flag:
        await my_group_level.finish(image(b64=pic2b64(text2image(reply))))
    else:
        await my_group_level.finish(reply)