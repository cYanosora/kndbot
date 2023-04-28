from nonebot import on_command
from nonebot.internal.params import ArgPlainText
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, Message, GROUP, ActionFailed
from manager import Config
from utils.message_builder import custom_forward_msg
from utils.utils import get_message_img
from .data_source import upload_image_to_local, record_local_images, get_local_record
from nonebot.params import CommandArg, Arg, ArgStr
from typing import List
from .config import global_record


__plugin_name__ = "上传图片"
__plugin_type__ = "好康的"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    上传图片至指定公开图库
    乱七八糟的图传上来会被master制裁
    
    指令：
        查看图库                        ：查看当前有哪些已公开图库，你可以建议master开启新的图库分类
        收录图片                        ：查看当前被实际收录的pjsk同人图数量
        传图/上传图片 [图库] [图片]        ：注意空格
        连续传图 [图库]
    示例：
        上传图片 美图 [图片]
        传图 美图 [图片]
        连传 美图 [图片] * n张
    注意:
        使用"传图"指令时 如果一次消息中包含多张图片，会同时上传，如果消息分开发送，则只会上传一张图片
        使用"连续传图"指令时 接下来的所有消息中的图片都将收集起来，必须必须必须通过发送 “stop” 告诉bot停止收集，随后开始上传
        ==============================================================================
        无法直接上传图至pjsk同人图库，pjsk同人图库中的图需要master审核分类
        但你可以先传到公开图库中，master自己会不定期将未收录的pjsk同人图收录归类
        {global_record['date']}记录：目前群友传上来的图被实际收录到pjsk图库中的数量为：{global_record['num']}
""".strip()
__plugin_settings__ = {
    "cmd": ['传图', '上传图片', '连续传图']
}
record_img = on_command('记录图片', aliases={"收录图片"}, permission=GROUP | SUPERUSER, priority=5, block=True)
upload_img = on_command("上传图片", aliases={"传图 "}, permission=GROUP, priority=5, block=True)

continuous_upload_img = on_command(
    "连续上传图片", aliases={"连传", "连续传图"}, permission=GROUP, priority=5, block=True
)

show_gallery = on_command(
    "查看公开图库", aliases={"查看图库"}, permission=GROUP, priority=5, block=True
)


@record_img.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        curr_record = await get_local_record()
        await record_img.finish(f'当前群友上传的pjsk同人图收录数：{curr_record}')
    if str(event.user_id) not in bot.config.superusers:
        return
    args = msg.split()
    if len(args) < 2:
        await record_img.finish("必须提供图库、图片id。格式：记录图片[图库] *[图片id]")
    target_gall = args[0]
    target_imgs = args[1:]
    if target_gall not in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        await record_img.finish("不存在此图库，请重新触发指令！")
    result = await record_local_images(target_gall, [int(i) for i in target_imgs if i.isdigit()])
    await record_img.finish(result)


@show_gallery.handle()
async def _():
    x = "公开图库列表：\n"
    for i, e in enumerate(Config.get_config("image_management", "IMAGE_DIR_LIST")):
        x += f"\t{i+1}.{e}，"
    await show_gallery.send(x[:-1])


@upload_img.handle()
async def _(event: MessageEvent, state: T_State, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    img_list = get_message_img(event.json())
    if args and args in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        state["path"] = args
    if img_list:
        state["img_list"] = arg


@upload_img.got(
    "path",
    prompt=f"请选择要上传的图库\n- "
    + "\n- ".join(Config.get_config("image_management", "IMAGE_DIR_LIST")),
)
@upload_img.got("img_list", prompt="现在可以把图发给我惹(/▽＼)")
async def _(
    bot: Bot,
    event: MessageEvent,
    path: str = ArgPlainText("path"),
    img_list: Message = Arg("img_list"),
):
    img_list = get_message_img(img_list)
    isvalid = path in Config.get_config("image_management", "IMAGE_DIR_LIST")
    if not isvalid:
        if not img_list:
            await upload_img.finish("上传失败，不存在此图库！")
        else:
            await upload_img.finish("上传失败，在发送图片前请携带图库名！")
    if isvalid and not img_list:
        await upload_img.reject_arg("img_list", "现在可以把图发给我惹(/▽＼)")
    group_id = 0
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    result, mes_list = await upload_image_to_local(img_list, path, event.user_id, group_id)
    await upload_img.send(result)
    superuser = int(list(bot.config.superusers)[0])
    upload_msg = custom_forward_msg(mes_list, bot.self_id)
    try:
        await bot.call_api(
            'send_private_forward_msg',
            user_id=superuser,
            messages=upload_msg
        )
    except ActionFailed:
        pass


@continuous_upload_img.handle()
async def _(event: MessageEvent, state: T_State):
    path = get_message_img(event.json())
    if path in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        state["path"] = path
    state["img_list"] = []


@continuous_upload_img.got(
    "path",
    prompt=f"请选择要上传的图库\n- "
    + "\n- ".join(Config.get_config("image_management", "IMAGE_DIR_LIST")),
)
@continuous_upload_img.got("img", prompt="请开始发送图片吧【发送‘stop’为停止】")
async def _(
    bot: Bot,
    event: MessageEvent,
    img_list: List[str] = Arg("img_list"),
    path: str = ArgStr("path"),
    img: Message = Arg("img"),
):
    isvalid = path in Config.get_config("image_management", "IMAGE_DIR_LIST")
    if not isvalid:
        if len(img_list) == 0:
            await continuous_upload_img.finish("上传失败，不存在此图库！")
        else:
            await continuous_upload_img.finish("上传失败，在发送图片前请携带图库名！")
    if not img.extract_plain_text() == "stop":
        img = get_message_img(img)
        if img:
            for i in img:
                img_list.append(i)
        await continuous_upload_img.reject_arg("img", "再来一张！【发送‘stop’为停止】")
    group_id = 0
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    result, mes_list = await upload_image_to_local(img_list, path, event.user_id, group_id)
    await continuous_upload_img.send(result)
    superuser = int(list(bot.config.superusers)[0])
    upload_msg = custom_forward_msg(mes_list, bot.self_id)
    try:
        await bot.call_api(
            'send_private_forward_msg',
            user_id=superuser,
            messages=upload_msg
        )
    except ActionFailed:
        pass