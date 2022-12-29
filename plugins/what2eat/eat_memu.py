from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot, GROUP, Message, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.log import logger
from nonebot.rule import to_me
from ._utils import eating_manager


__plugin_name__ = "菜单管理 [Admin]"
__plugin_type__ = "今天吃什么"
__plugin_version__ = 0.1
__plugin_usage__ = """
usage：
    今天吃什么,群管额外指令
    指令：
        菜单           :查看群菜单
        添加菜品 [菜名] :添加菜品至群自定义菜单
        移除菜品 [菜名] :从菜单移除菜品
""".strip()
__plugin_superuser_usage__ = """
superuser_usage：
    今天吃什么，超管额外指令
    指令：
        加菜      ：添加菜品至基础菜单
"""
__plugin_settings__ = {
    "admin_level": 2,
    "cmd": ["菜单管理", "菜单"],
}


add_group = on_command("添加菜品", permission=GROUP, priority=5, block=True)
remove_food = on_command("移除菜品", permission=GROUP, priority=5, block=True)
show_group = on_command(
    "菜单", aliases={"群菜单", "查看菜单"}, rule=to_me(), permission=GROUP, priority=5, block=True
)
add_basic = on_command("加菜", permission=SUPERUSER, priority=5, block=True)


@add_group.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if not args:
        await add_group.finish("还没输入你要添加的菜品呢~", at_sender=True)
    elif args and len(args) == 1:
        new_food = args[0]
        user_id = str(event.user_id)
        logger.info(f"User {user_id} 添加了 {new_food} 至菜单")
        msg = eating_manager.add_group_food(new_food, event)
        await add_group.finish(msg, at_sender=True)
    else:
        await add_group.finish("添加菜品参数错误~", at_sender=True)


@add_basic.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if not args:
        await add_basic.finish("还没输入你要添加的菜品呢~", at_sender=True)
    elif args and len(args) == 1:
        new_food = args[0]
        user_id = str(event.user_id)
        logger.info(f"Superuser {user_id} 添加了 {new_food} 至基础菜单")
        msg = eating_manager.add_basic_food(new_food)
        await add_basic.finish(msg, at_sender=True)
    else:
        await add_basic.finish("添加菜品参数错误~", at_sender=True)


@remove_food.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split()
    if not args:
        await remove_food.finish("还没输入你要移除的菜品呢~", at_sender=True)
    elif args and len(args) == 1:
        food_to_remove = args[0]
        user_id = str(event.user_id)
        logger.info(f"User {user_id} 从菜单移除了 {food_to_remove}")
        msg = eating_manager.remove_food(food_to_remove, event)
        await remove_food.finish(msg, at_sender=True)
    else:
        await remove_food.finish("移除菜品参数错误~", at_sender=True)


@show_group.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    msg = eating_manager.show_group_menu(event)
    await show_group.finish(msg, at_sender=True)


