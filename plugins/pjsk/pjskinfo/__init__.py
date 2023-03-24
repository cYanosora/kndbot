import datetime
from typing import Any, Tuple
from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import Message, ActionFailed, MessageEvent
from nonebot.params import CommandArg, RegexGroup
from services import logger
from utils.http_utils import AsyncHttpx
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from .._config import data_path
from .._song_utils import get_songs_data, parse_bpm, save_songs_data, info, idtoname
from .._models import PjskSongsAlias
import json

__plugin_name__ = "歌曲查询/pjskinfo"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤曲目信息
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询4次
    指令：
        pjskinfo/song [曲目]                : 查看曲目详细信息
        pjskset [曲目别称] to [曲目]          : 给对应曲目添加别称
        pjskdel [曲目别称]                   : 删除曲目的对应别称
        pjskalias [曲目]                    : 查询曲目所有别称
        bpm/pjskbpm [曲目]                  : 查询曲目bpm
        查物量  [总combo数]                  : 查询对应物量的曲目
        查bpm  [bpm]                       : 查询对应bpm的曲目
    数据来源：
        pjsekai.moe
        unipjsk.com
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["pjskinfo", "烧烤相关", "uni移植", "歌曲查询"],
}
__plugin_cd_limit__ = {
    "cd": 60, "count_limit": 4, "rst": "别急，等[cd]秒后再用！", "limit_type": "user"
}
__plugin_block_limit__ = {"rst": "别急，还在查！"}

# pjskinfo
pjskinfo = on_command('pjskinfo', aliases={"song"}, priority=5, block=True)

# pjskset
pjskset = on_regex(r'^pjskset(.+to.+)', priority=5, block=True)

# pjskdel
pjskdel = on_command('pjskdel', priority=5, block=True)

# pjskalias
pjskalias = on_command('pjskalias', priority=5, block=True)

# pjskbpm
pjskbpm = on_command('pjskbpm', aliases={'bpm'}, priority=5, block=True)

# 查物量
pjsknotecount = on_command('查物量', priority=5, block=True)

# 查bpm
pjskbpmfind = on_command('查bpm', priority=5, block=True)


@pjskinfo.handle()
async def _(msg: Message = CommandArg()):
    arg = msg.extract_plain_text().strip()
    if not arg:
        await pjskinfo.finish("使用方法：pjskinfo + 曲名")
    # 首先查询本地数据库有无对应别称id
    data = await get_songs_data(arg, isfuzzy=False)
    # 若无结果则访问uniapi
    if data['status'] != 'success':
        url = rf'https://api.unipjsk.com/getsongid/{arg}'
        data = (await AsyncHttpx.get(url)).json()
        # 无结果则尝试在本地模糊搜索得到结果
        if data['status'] != 'success':
            data = await get_songs_data(arg, isfuzzy=True)
            # 若还无结果则说明没有歌曲信息
            if data['status'] != 'success':
                await pjskinfo.finish('没有找到你要的歌曲哦')
        # 有结果则尝试更新api返回的别称信息存入本地数据库
        else:
            await save_songs_data(data['musicId'])
    text = "你要找的可能是：" if data['match'] < 0.8 else ""
    leak, imgb64 = await info(data['musicId'])
    if leak:
        text += f"匹配度:{round(data['match'], 4)}\n⚠该内容为剧透内容"
    elif data['translate'] == '':
        text += f"{data['title']}\n匹配度:{round(data['match'], 4)}"
    else:
        text += f"{data['title']} ({data['translate']})\n匹配度:{round(data['match'], 4)}"
    imgpath = data_path / f"pjskinfo/pjskinfo_{data['musicId']}.png"
    if not imgpath.exists() and imgb64:
        img = image(b64=imgb64)
    else:
        img = image(imgpath)
    await pjskinfo.finish(text + img)


@pjskalias.handle()
async def _(msg: Message = CommandArg()):
    arg = msg.extract_plain_text().strip()
    if arg:
        # 首先查询本地数据库有无对应别称id
        data = await get_songs_data(arg, isfuzzy=False)
        # 若无结果则访问uniapi
        if data['status'] != 'success':
            url = rf'https://api.unipjsk.com/getsongid/{arg}'
            data = (await AsyncHttpx.get(url)).json()
            # 无结果则尝试在本地模糊搜索得到结果
            if data['status'] != 'success':
                data = await get_songs_data(arg, isfuzzy=True)
                # 若还无结果则说明没有歌曲信息
                if data['status'] != 'success':
                    await pjskinfo.finish('没有找到你要的歌曲哦')
            # 有结果则尝试更新api返回的别称信息存入本地数据库
            else:
                await save_songs_data(data['musicId'])
        if data['musicId'] == 0:
            await pjskalias.finish("没有找到你要的歌曲哦")
        musicid = data['musicId']
        if data['translate'] == '':
            returnstr = f"{data['title']}\n匹配度:{round(data['match'], 4)}\n"
        else:
            returnstr = f"{data['title']} ({data['translate']})\n匹配度:{round(data['match'], 4)}\n"
        alias = await PjskSongsAlias.query_alias(musicid)
        if alias:
            returnstr += "已有的别称：" + "，".join(alias)
        else:
            returnstr += "此曲暂无别称"
        try:
            await pjskalias.finish(returnstr)
        except ActionFailed:
            await pjskalias.finish(
                image(b64=pic2b64(text2image(returnstr))),
                at_sender=True
            )
    else:
        await pjskalias.finish("请使用正确格式：pjskalias昵称")


@pjskset.handle()
async def _(event: MessageEvent, reg_group: Tuple[Any, ...] = RegexGroup()):
    msg = reg_group[0].strip()
    # 对别名和称呼做特殊处理，以防别名中本身含有关键词to
    index = 0
    oldalias = newalias = ""
    oldsid = 0
    for i in range(msg.count('to')):
        index = msg.find('to', index)
        tmp_new, tmp_old = msg[:index].strip(), msg[index + 2:].strip()
        index = index + 2
        # 一旦找到chara在已有称呼表内，则可以识别alias的位置
        oldsid = await PjskSongsAlias.query_sid(tmp_old)
        if oldsid:
            oldalias = tmp_old
            newalias = tmp_new
            break
    if not oldsid or not oldalias or not newalias:
        await pjskset.finish("添加失败，可能是找不到对应称呼", at_sender=True)
    elif oldalias == newalias:
        await pjskset.finish("添加失败，新称呼与旧称呼相同", at_sender=True)
    group_id = -1
    if hasattr(event, 'group_id'):
        group_id = event.group_id
    if await PjskSongsAlias.add_alias(
        oldsid, newalias, event.user_id, group_id, datetime.datetime.now(), False
    ):
        with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for musics in data:
                if musics['id'] == oldsid:
                    title = musics['title']
                    break
        await pjskset.finish(f"设置成功！{newalias}->{title}")
    else:
        newsid = await PjskSongsAlias.query_sid(newalias)
        with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for musics in data:
                if musics['id'] == newsid:
                    title = musics['title']
                    break
        if title:
            await pjskset.finish(f"添加失败，此称呼已经属于歌曲：{title}", at_sender=True)
        else:
            await pjskset.finish(f"添加失败，此称呼已经属于其它歌曲", at_sender=True)


@pjskdel.handle()
async def _(event: MessageEvent, msg: Message = CommandArg()):
    arg = msg.extract_plain_text().strip()
    sid = await PjskSongsAlias.query_sid(arg)
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        for musics in data:
            if musics['id'] == sid:
                songname = musics['title']
                break
        else:
            songname = ""
    if await PjskSongsAlias.delete_alias(arg):
        await pjskdel.finish(
            f"已成功删除歌曲:{songname}的别称:{arg}"
            if songname else "删除成功！",
            at_sender=True
        )
        qq = event.user_id
        group = -1
        if hasattr(event, 'group_id'):
            group= event.group_id
        logger.info(f"USER {qq} GROUP {group} 删除了{songname}的称呼 {arg} ！")
    else:
        await pjskdel.finish(f"删除失败，找不到歌曲", at_sender=True)


@pjskbpm.handle()
async def _(msg: Message = CommandArg()):
    arg = msg.extract_plain_text().strip()
    if not arg:
        await pjskbpm.finish("使用方法：pjskbpm + 曲名")
    # 首先查询本地数据库有无对应别称id
    data = await get_songs_data(arg, isfuzzy=False)
    # 若无结果则访问uniapi
    if data['status'] != 'success':
        url = rf'https://api.unipjsk.com/getsongid/{arg}'
        data = (await AsyncHttpx.get(url)).json()
        # 无结果则尝试在本地模糊搜索得到结果
        if data['status'] != 'success':
            data = await get_songs_data(arg, isfuzzy=True)
            # 若还无结果则说明没有歌曲信息
            if data['status'] != 'success':
                await pjskbpm.finish('没有找到你要的歌曲哦')
        # 有结果则尝试更新api返回的别称信息存入本地数据库
        else:
            await save_songs_data(data['musicId'])
    text = ''
    bpm = await parse_bpm(data['musicId'])
    for bpms in bpm[1]:
        text = text + ' - ' + str(bpms['bpm']).replace('.0', '')
    text = f"{data['title']}\n匹配度:{round(data['match'], 4)}\nBPM: " + text[3:]
    await pjskbpm.finish(text)


@pjsknotecount.handle()
async def _(msg: Message = CommandArg()):
    notes = msg.extract_plain_text().strip()
    try:
        notes = int(notes)
    except:
        await pjsknotecount.finish("请输入数字！")
    text = ''
    with open(data_path / 'musicDifficulties.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        musics = json.load(f)
    for i in data:
        if i['totalNoteCount'] == notes:
            text += f"{idtoname(i['musicId'], musics)}[{(i['musicDifficulty'].upper())} {i['playLevel']}]\n"
    if text == '':
        text = '没有找到'
    await pjsknotecount.finish(text)


@pjskbpmfind.handle()
async def _(msg: Message = CommandArg()):
    targetbpm = msg.extract_plain_text().strip()
    try:
        targetbpm = int(targetbpm)
    except:
        await pjskbpmfind.finish("请输入数字！")
    bpm = {}
    text = ''
    with open(data_path / 'musics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    for music in data:
        bpm[music['id']] = await parse_bpm(music['id'])[1]
    for musicid in bpm:
        for i in bpm[musicid]:
            if int(i['bpm']) == targetbpm:
                bpmtext = ''
                for bpms in bpm[musicid]:
                    bpmtext += ' - ' + str(bpms['bpm']).replace('.0', '')
                text += f"{idtoname(musicid)}: {bpmtext[3:]}\n"
                break
    if text == '':
        text = '没有找到'
    await pjskbpmfind.finish(text)

