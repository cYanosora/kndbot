from nonebot import on_command
from nonebot.internal.matcher import Matcher
from nonebot.typing import T_State
from configs.path_config import IMAGE_PATH
from utils.limit_utils import access_count, access_cd
from utils.message_builder import image, custom_forward_msg
from services.log import logger
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, GROUP, Bot, NetworkError
from utils.utils import cn2py
from manager import Config
from manager import withdraw_message_manager, plugins2count_manager
from .rule import rule
import random
import os
try:
    import ujson as json
except ModuleNotFoundError:
    import json
try:
    from ..pjsk_images.pjsk_image import pjsk_get_pic, pjsk_get_path_and_len
    pjsk_flag = True
except:
    pjsk_flag = False


__plugin_name__ = "本地图库/看图"
__plugin_type__ = "好康的"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    发送指定烧烤图库下的随机or指定序号范围内的图片，同人图全为master个人整理分类后的收藏(-ω- )
    指令：
        看|来点|来丶 [图库名] *[图片序号列表]
        注意：[图片序号列表]为空时随机抽图，可用单个数字表示指定序号
        若需要同时指定多张请用使用中英文逗号或空格分隔,也可以使用 - 符号指定范围
    附加图库:
        烧烤图库以外的公开图库如下(此类公开图库可以使用 '传图/连传' 功能回馈好康的图给master)
            {"/".join(Config.get_config("image_management", "IMAGE_DIR_LIST"))}
            
    ↓↓↓听不懂没关系，看下面的例子↓↓↓
    示例: 
        ### 对于单人
        看宵崎奏            随机发送1张knd同人图
        来点奏宝 1-25       依次发送图库中 id为1至25的 knd同人图
        来点奏宝 1,2,3,4    依次发送图库中 id为1、2、3、4的 knd同人图
        来点奏宝 1 2 3 4 5  依次发送图库中 id为1、2、3、4、5的 knd同人图
        
        ### 对于团体
        来丶25 25          发送图库中 id为25 的25时cp图(基本上是一些弱cp向、全家福、以及和虚拟歌姬贴贴的图，其他组合同理)
        
        ### 对于cp/cb (不止以下cp，更多其他cp如果不清楚cp名是可以查询的、之后自行添加合适的称呼也行，详见 角色称呼 功能)
        来丶knmf 25        发送图库中 id为25 的k雪cp图(实际上不分左右，其他cp同理)
        来点姐弟            随机发送姐弟cp(×)cb(√)图
        来点杂图            随机发送一些小众cp/cb图(实际上是有懒狗不想单独分类所以丢一块儿了(´ε｀；))
        来点cp             随机发送任意cp图(超大盲盒，DD党专用)
        
    ↓↓↓以下为与实际使用体验无关的master碎碎念↓↓↓
    注意：
        若发现图库中的图有分类错误的现象(这点真的很抱歉)，方便的话，请使用你一点点时间通过 滴滴滴 功能来告知master
        以及图库中的推图所标记的出处也许会因为画师删推、改名、废号等原因而导致找不到原图，方便的话也请告知master
        还有图库中的某些图并未标记出处(早期历史遗留问题)，若有人知道出处的话，还望能告知master
        然后若有各位觉得收藏不当的图也可以联系master删除
        master精力有限，如果能得到大家的提醒，master会以能到达的最快速度解决这些问题
        ======================================================================================
        烧烤角色的昵称管理详见 '角色昵称/别名' 功能(便于使用角色称呼发图)
        此功能主要用于指路，为提高发图速度，部分图已经受压制处理，有存图需求还请从图源处获取(重要)
        ======================================================================================
        图库内质量参差不齐、画风多变请见谅，master只是将自己见到的觉得还可以的同人图都公开分享出来而已
        所以请勿抱以欣赏官图的心态，指责我xp有问题随你便，但请不要辱骂画师，否则我可不知道会发生什么
        各团同人图数量相差过大与个人偏好以及同人圈热度有关，但绝无故意拉大差距的意思，烤的米娜都很好我DD真的不挑
        另外虽然已将单人、cp图分在不同图库内，但实际上仍有极少一部分单人图可能略微地带有一些cp倾向
        ======================================================================================
        限制群内1分钟内最多使用4次，一次至多25张，每人每日最多看100张，防止有人吃撑死(´∀｀；)
""".strip()
__plugin_settings__ = {
    "cmd": ["看图", "本地图库"]
}
__plugin_cd_limit__ = {"cd": 60, "limit_type": "group", "count_limit": 4, "rst": "请[cd]s后再看呢(￣▽￣)"}
__plugin_count_limit__ = {
    "max_count": 100,
    "limit_type": "user",
    "rst": "你今天已经看了[count]次啦，还请明天再看呢（。＾▽＾）[at]",
}
__plugin_block_limit__ = {}

send_img = on_command("来点", aliases={"看", "来丶"},permission=GROUP, rule=rule(), priority=5, block=True)
_path = IMAGE_PATH / "image_management"


def count_check(module: str, event: MessageEvent, bot: Bot, num: int) -> int:
    """
    插件内检查使用次数是否超标，超标返回剩余使用次数，未超标返回0
    """
    if (
        plugins2count_manager.check_plugin_count_status(module)
        and str(event.user_id) not in bot.config.superusers
    ):
        plugin_count_data = plugins2count_manager.get_plugin_count_data(module)
        limit_type = plugin_count_data["limit_type"]
        count_type_ = event.user_id
        if limit_type == "group" and isinstance(event, GroupMessageEvent):
            count_type_ = event.group_id
        # 使用次数耗尽
        use_count = plugins2count_manager.get_daily_used_count(module, count_type_)
        max_count = plugins2count_manager.get_count(module)
        if use_count + num > max_count:
            return max_count - use_count
        else:
            return 0


@send_img.handle()
async def _(matcher: Matcher, bot: Bot, event: GroupMessageEvent, state: T_State):
    gallery = state["sendpic_name"]
    img_ids = state['sendpic_imgid']
    # 优先在默认图库中匹配
    if gallery in Config.get_config("image_management", "IMAGE_DIR_LIST"):
        path = _path / cn2py(gallery)
        if gallery in Config.get_config("image_management", "IMAGE_DIR_LIST"):
            if not path.exists() and (path.parent.parent / cn2py(gallery)).exists():
                path = IMAGE_PATH / cn2py(gallery)
            else:
                path.mkdir(parents=True, exist_ok=True)
        length = len(os.listdir(path))
        if length == 0:
            logger.warning(f'图库 {cn2py(gallery)} 为空，调用取消！')
            await send_img.finish("该图库中没有图片噢")
        if not img_ids:
            img_ids = [random.randint(0, length - 1)]
        for index in img_ids:
            if int(index) > length - 1:
                img_ids[img_ids.index(index)] = length - 1
            elif int(index) < 0:
                img_ids[img_ids.index(index)] = 0
        img_ids = sorted(set(img_ids))
        access_count(matcher.plugin_name, event, len(img_ids))
        access_cd(matcher.plugin_name, event, len(img_ids))
        if len(img_ids) == 1:
            index = img_ids[0]
            result = image(path / f"{index}.jpg")
            if result:
                logger.info(
                    f"(USER {event.user_id}, GROUP {event.group_id}) "
                    f"发送{cn2py(gallery)}"
                    f"图片序号: {index}"
                )
                msg_id = await send_img.send(
                    f"id：{index}" + result
                    if Config.get_config("image_management", "SHOW_ID")
                    else "" + result
                )
                withdraw_message_manager.withdraw_message(
                    event,
                    msg_id,
                    Config.get_config("image_management", "WITHDRAW_IMAGE_MESSAGE"),
                )
            else:
                logger.info(
                    f"(USER {event.user_id}, GROUP {event.group_id}) "
                    f"发送 {cn2py(gallery)} 失败"
                )
                await send_img.finish(f"不知道为什么，总之不想给你看OvO", at_sender=True)
        else:
            end = count_check(matcher.plugin_name, event, bot, len(img_ids))
            if end:
                await send_img.send("指定张数超过当日上限，只有部分图片可以发送")
                img_ids = img_ids[:end]
            await send_img.send("正在整理图片中，请耐心等待(－ω－)", at_sender=True)
            mes_list = []
            for index in img_ids:
                result = image(path / f"{index}.jpg")
                if result:
                    mes_list.append(
                        f"id：{index}" + result
                        if Config.get_config("image_management", "SHOW_ID")
                        else "" + result
                    )
                else:
                    mes_list.append(
                        f"id：{index}\n这张图片出错了，可能是不想给你看OvO"
                        if Config.get_config("image_management", "SHOW_ID")
                        else "这张图片出错了，可能是不想给你看OvO"
                    )
            mes_list = custom_forward_msg(mes_list, bot.self_id)
            await send_img.send("图片整理完毕(｡･ω･)", at_sender=True)
            msg_id = await bot.send_group_forward_msg(group_id=event.group_id, messages=mes_list)
            logger.info(
                f"(USER {event.user_id}, GROUP {event.group_id}) "
                f"发送{cn2py(gallery)}"
                f"一共{len(img_ids)}张：{img_ids}"
            )
            withdraw_message_manager.withdraw_message(
                event,
                msg_id,
                Config.get_config("image_management", "WITHDRAW_IMAGE_MESSAGE"),
            )
    # 排除是特殊词汇的图库
    else:
        for each in Config.get_config("pjsk_alias", "BANWORDS"):
            banword, banreply = each.split("_")
            if banword == gallery and banreply == "0":
                return
            elif banword == gallery:
                await send_img.finish(f'看什么看，你根本就没有{banreply}！', at_sender=True)
                return
    # 如果有pjsk角色搜图功能模块，使用烧烤图库
    if pjsk_flag:
        # 查询图库名路径与图片总数
        path, length = pjsk_get_path_and_len(gallery)
        print(path, length)
        if not path:
            logger.warning("pjsk搜图模块文件路径不存在！")
            await send_img.finish("出错了，请稍后再试！>_<")
            return
        # 规范化用户输入的图片id
        for index in img_ids:
            if index > length:
                img_ids[img_ids.index(index)] = length
            elif index <= 0:
                img_ids[img_ids.index(index)] = 1
        img_ids = sorted(set(img_ids))
        # 检查用户剩余看图次数
        if len(img_ids) > 1:
            print(len(img_ids))
            end = count_check(matcher.plugin_name, event, bot, len(img_ids))
            if end:
                await send_img.send(f"指定张数超过当日使用上限，只有{end+1}张图片可以发送(－ω－)", at_sender=True)
                img_ids = img_ids[:end]
            else:
                await send_img.send("正在整理图片中，请耐心等待(｡･ω･)", at_sender=True)
        # 根据图库名路径和图片id获取图片
        result = pjsk_get_pic(path, img_ids)
        if result:
            try:
                logger.info(f"USER {event.user_id} 调用pjsk搜图功能，图片路径:{path}")
                if len(result) == 1:
                    msg_id = await send_img.finish(result[0])
                    withdraw_message_manager.withdraw_message(
                        event,
                        msg_id,
                        Config.get_config("image_management", "WITHDRAW_IMAGE_MESSAGE"),
                    )
                else:
                    msg_id = await bot.send_group_forward_msg(group_id=event.group_id, messages=custom_forward_msg(result, bot.self_id))
                    withdraw_message_manager.withdraw_message(
                        event,
                        msg_id,
                        Config.get_config("image_management", "WITHDRAW_IMAGE_MESSAGE"),
                    )
            except NetworkError as e:
                logger.warning(f"pjsk搜图发送消息超时，Error: {e}")
                await send_img.finish("发送超时，可能是bot网不好。")
                return
            else:
                access_count(matcher.plugin_name, event, len(result))
                access_cd(matcher.plugin_name, event, 1)
        else:
            logger.warning("pjsk搜图无结果")
            await send_img.finish("出错了，请稍后再试！>_<")
