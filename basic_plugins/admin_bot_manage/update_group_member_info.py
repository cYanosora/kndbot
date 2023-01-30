from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, GROUP, Message
from nonebot.params import CommandArg
from utils.utils import is_number
from ._data_source import update_member_info

__plugin_name__ = "更新群组成员列表 [Admin]"
__plugin_type__ = "群相关"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    更新群组成员的基本信息
    指令：
        更新群组成员列表/更新群组成员/更新群成员
    效果：
        让bot更新变化的群成员信息，用于bot没有检测到群员人数变化、权限变化等的情况下
        比如说bot掉线or关机的情况下群成员发生变化时
        一般不需要使用，总之会自己更新
""".strip()
__plugin_superuser_usage__="""
superuser_usage:
    跨群更新群组成员的基本信息
    指令：
        更新群成员/更新群组成员列表/更新群组成员信息 [群号]
""".strip()
__plugin_settings__ = {
    "admin_level": 1,
    "cmd": ["更新群组成员列表", "更新群成员列表", "更新群成员"]
}


refresh_member_group = on_command(
    "更新群组成员列表", aliases={"更新群组成员", "更新群成员"}, permission=GROUP, priority=3, block=True
)


@refresh_member_group.handle()
async def _(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    group_id = arg.extract_plain_text().strip()
    if group_id:
        if not str(event.user_id) in bot.config.superusers:
            return
        if is_number(group_id):
            if await update_member_info(bot, int(group_id)):
                await refresh_member_group.finish("更新群员信息成功！", at_sender=True)
            else:
                await refresh_member_group.finish("更新群员信息失败！", at_sender=True)
        else:
            await refresh_member_group.finish(f"请输入正确的群号", at_sender=True)
    else:
        if await update_member_info(bot, event.group_id):
            await refresh_member_group.finish("更新群员信息成功！", at_sender=True)
        else:
            await refresh_member_group.finish("更新群员信息失败！", at_sender=True)
