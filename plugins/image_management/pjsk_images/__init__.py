from datetime import datetime
from typing import Tuple, Any
from nonebot.permission import SUPERUSER
from configs.path_config import RESOURCE_PATH
from manager import Config
from services.log import logger
from nonebot import on_regex, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP
from nonebot.params import RegexGroup
from utils.imageutils import Text2Image, BuildImage as IMG, union, pic2b64
from utils.message_builder import image
from .pjsk_alias_init import init_default_pjsk_alias
from .pjsk_db_source import PjskAlias
from .pjsk_config import pjsk_info_all, pjsk_info_dict, pjsk_info_mapping, pjsk_cp_dict, cpmap

__plugin_name__ = "烧烤角色称呼"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    管理pjsk角色/组合称呼，防止与unibot指令冲突故有所不同，功能是类似的
    指令：
        info[昵称]                    查看此角色所有昵称
        add[昵称]to[角色名]            添加全群可见的角色昵称
        gradd[昵称]to[角色名]          添加仅在本群可见的角色昵称
        del[昵称]                     删除角色昵称，优先删除群内昵称
        cpinfo                       查看团外cp默认的昵称(不清楚哪些团外cp有对应图库时使用)
        cpinfo [组合名]               查看该团体下所有cp默认的昵称(不清楚团内cp名时使用)
    注意:
        此功能主要是为了能方便看角色同人图等等
        所以不要设置不合适的称呼，也不要乱删称呼，谢谢
        尤其是knd的某些低俗无端谐音梗，谁加了请自觉删除
        如果等master来删，那么会顺带赠送拉黑套餐不谢
""".strip()
__plugin_settings__ = {
    "cmd": ["别名", "角色称呼", "角色别名"],
}

# 添加角色别名
pjsk_alias_add = on_regex(r'^(gr)?add(.+to.+)', permission=SUPERUSER | GROUP, priority=5, block=True)

# 删除角色别名
pjsk_alias_del = on_regex(r'^del(.*)', permission=SUPERUSER | GROUP, priority=5, block=True)

# 查看角色别名
pjsk_alias_info = on_regex(r'^info(.*)', permission=GROUP, priority=5, block=True)

# 查看cp别名
pjsk_cp_info = on_regex("^cpinfo(.*)", permission=GROUP, priority=5, block=True)

# 自主调用初始化别名
pjsk_alias_initial = on_command("初始化称呼", permission=SUPERUSER, priority=4, block=True)

map = pjsk_info_mapping



@pjsk_alias_add.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    cmd = reg_group[0]
    msg = reg_group[1].strip()
    qq = event.user_id
    group = event.group_id
    # 对新旧昵称做特殊处理，以防新昵称中本身含有关键词to
    index = 0
    alias = chara = ""
    for i in range(msg.count('to')):
        index = msg.find('to', index)
        tmp_alias, tmp_chara = msg[:index].strip(), msg[index + 2:].strip()
        index = index + 2
        # 一旦找到旧昵称在已有称呼表内，则可以识别新昵称的位置
        if tmp_chara in pjsk_info_all or await PjskAlias.query_name(tmp_chara, group_id=group):
            alias = tmp_alias
            chara = tmp_chara
            break
    if not chara or not alias:
        await pjsk_alias_add.finish("添加失败，可能是找不到对应称呼!", at_sender=True)
    elif alias == chara:
        await pjsk_alias_add.finish("添加失败，你要不看看自己在说什么!", at_sender=True)
    # 排除违禁称呼
    for each in Config.get_config("pjsk_alias", "BANWORDS"):
        if each.split('_')[0] == alias:
            await pjsk_alias_add.finish("你不要乱加奇奇怪怪的称呼哦?!"
                                        + image("chujing.jpg", "kanade"), at_sender=True)
            return
    # 当新昵称是主名时
    if alias in pjsk_info_all:
        key = await PjskAlias.query_name(chara, group_id=group)
        if alias == key:
            await pjsk_alias_add.finish(f"此昵称已经默认属于{cpmap.get(key) or map.get(key)}了哦", at_sender=True)
        else:
            await pjsk_alias_add.finish(f"你不要乱取名的呀！", at_sender=True)
        return
    # 仅为群内昵称
    is_pass = False if cmd == 'gr' else True

    # 若旧昵称不是主名，先转化为主名
    if chara not in pjsk_info_all:
        true_chara = await PjskAlias.query_name(chara, group_id=group)
        if not true_chara:
            await pjsk_alias_add.finish("添加失败，还没有角色/组合叫这个的哦", at_sender=True)
            return
    else:
        true_chara = chara
    if true_chara == "other":
        await pjsk_alias_add.finish("添加失败，此图库无法指定新昵称", at_sender=True)
    # 添加新昵称
    flag = await PjskAlias.add_alias(true_chara, alias, event.user_id, event.group_id, datetime.now(), is_pass)
    if flag:
        await pjsk_alias_add.finish(
            f"成功添加{'全局' if is_pass else '群内'}称呼:{alias}->{cpmap.get(true_chara) or map.get(true_chara)}!",
            at_sender=True
        )
        logger.success(
            f"USER {qq} GROUP {group} 为 {true_chara} 添加了 {'全局' if is_pass else '群内'} 称呼 {alias} ！"
        )
    else:
        key = await PjskAlias.query_name(alias, group_id=group)
        await pjsk_alias_add.finish(f"此称呼已经属于{cpmap.get(key) or map.get(key)}了哦~", at_sender=True)
        return


@pjsk_alias_del.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    alias = reg_group[0].strip()
    if not alias:
        return
    if alias in pjsk_info_all:
        await pjsk_alias_del.finish("这是默认称呼哦，别乱删！", at_sender=True)
    key = await PjskAlias.query_name(alias, group_id=event.group_id)
    flag = await PjskAlias.delete_alias(alias, group_id=event.group_id)
    if flag:
        x = "角色" if key in [j for i in pjsk_info_dict.keys() for j in pjsk_info_dict[i]] else "组合"
        await pjsk_alias_del.finish(f"已成功删除{x}{cpmap.get(key) or map.get(key)}的称呼{alias}", at_sender=True)
        qq = event.user_id
        group = event.group_id
        logger.success(
            f"USER {qq} GROUP {group} 删除了{key}的称呼 {alias} ！"
        )
    else:
        await pjsk_alias_del.finish(f"删除失败，还没有角色/组合叫这个的哦", at_sender=True)


@pjsk_alias_info.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    alias = reg_group[0].strip()
    if not alias:
        return
    if alias in pjsk_info_all:
        grresult = await PjskAlias.query_alias(alias, group_id=event.group_id)
        glresult = await PjskAlias.query_alias(alias)
    else:
        alias = await PjskAlias.query_name(alias, group_id=event.group_id)
        if alias:
            grresult = await PjskAlias.query_alias(alias, group_id=event.group_id)
            glresult = await PjskAlias.query_alias(alias)
        else:
            await pjsk_alias_info.finish("还没有角色/组合叫这个的哦", at_sender=True)
            return
    x = "角色" if alias in [j for i in pjsk_info_dict.keys() for j in pjsk_info_dict[i]] else "组合"
    glalias_str = f"{x}{cpmap.get(alias) or map.get(alias)}的全局称呼：\n{alias}，" + "，".join(glresult) if glresult else None
    gralias_str = f"\n群内称呼：\n" + '，'.join(grresult) if grresult else None
    reply = glalias_str if glalias_str else ""
    reply += gralias_str if gralias_str else ""
    await pjsk_alias_info.finish(reply)


@pjsk_cp_info.handle()
async def _(event: GroupMessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    alias = reg_group[0].strip()
    # 未输入alias时，默认查询团外cp
    if not alias:
        cps = pjsk_info_dict['cp'].copy()
        cps.remove("other")
    # 当输入了alias时，查询对应团体下的所有cp名
    else:
        if alias not in pjsk_cp_dict.keys():
            alias = await PjskAlias.query_name(alias, group_id=event.group_id)
        cps = pjsk_cp_dict.get(alias, None)
        if cps is None:
            await pjsk_cp_info.finish("只能输入团队的名称！", at_sender=True)

    reply_img_list = []
    w = h = 0
    pjsk_chara2id = {
        'ick': 1, 'saki': 2, 'hnm': 3, 'shiho': 4,
        'mnr': 5, 'hrk': 6, 'airi': 7, 'szk': 8,
        'khn': 9, 'an': 10, 'akt': 11, 'toya': 12,
        'tks': 13, 'emu':14, 'nene': 15, 'rui': 16,
        'knd': 17, 'mfy': 18, 'ena': 19, 'mzk': 20,
        'miku': 21, 'rin': 22, 'len': 23, 'luka': 24, 'meiko': 25, 'kaito': 26
    }
    for cp in cps:
        grresult = await PjskAlias.query_alias(cp, group_id=event.group_id)
        glresult = await PjskAlias.query_alias(cp)
        if cpname := cpmap.get(cp):
            cpids = [pjsk_chara2id.get(x, 0) for x in cpname.split('×')]
            cpimg = union(
                [IMG.open(RESOURCE_PATH / "masterdata" / "chara" / f"chr_ts_{i}.png").resize((30, 30)).image
                for i in cpids],
                interval=2, type='col'
            )
            reply = f"的称呼：{cp}" + ("，" + "，".join(glresult) if glresult else "")
            reply += ('，' + '，'.join(grresult)) if grresult else ""
            textimg = Text2Image.from_text(
                reply,
                fontsize=20,
                fontname="SourceHanSansCN-Regular.otf",
            ).to_image()
            reply_img_list.append(union(
                [cpimg, textimg],
                interval=3, type='col', bk_color='white'
            ))
            w = textimg.width if textimg.width > w else w
            h += textimg.height
    pad = 10
    bk = union(reply_img_list, interval=pad, padding=(pad,pad,pad,pad), align_type='left', type='row', bk_color='white')
    await pjsk_cp_info.finish(image(b64=pic2b64(bk)))


@pjsk_alias_initial.handle()
async def _():
    await init_default_pjsk_alias()
