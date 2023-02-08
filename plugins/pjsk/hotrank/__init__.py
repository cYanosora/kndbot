import os
import time
from PIL import Image, ImageDraw, ImageFont
from nonebot import on_command
from configs.path_config import FONT_PATH
from utils.imageutils import pic2b64
from utils.message_builder import image
from .._config import data_path
try:
    import ujson as json
except:
    import json

__plugin_name__ = "热度排行"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    查询烧烤热度排行
    移植自unibot(一款功能型烧烤bot)
    若群内已有unibot请勿开启此bot该功能
    私聊可用，限制每人1分钟只能查询1次
    指令：
        热度排行
    数据来源：
        pjsekai.moe
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["热度排行", "烧烤相关", "uni移植"],
}
__plugin_cd_limit__ = {"cd": 60, "count_limit": 1, "rst": "别急，等[cd]秒后再用！", "limit_type": "user"}
__plugin_block_limit__ = {"rst": "别急，还在查！"}


# pjsk热度排行
pjsk_hotrank = on_command('热度排行', priority=5, block=True)


@pjsk_hotrank.handle()
async def _():
    with open(data_path / 'realtime/musics.json', 'r', encoding='utf-8') as f:
        musics = json.load(f)
    for i in range(0, len(musics)):
        try:
            musics[i]['hot']
        except KeyError:
            musics[i]['hot'] = 0
    musics.sort(key=lambda x: x["hot"], reverse=True)
    text = ''
    for i in range(0, 40):
        text = text + f"{i + 1} {musics[i]['title']} ({int(musics[i]['hot'])})\n"
    IMG_SIZE = (500, 40 + 33 * 34)
    img = Image.new('RGB', IMG_SIZE, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 18)
    draw.text((20, 20), '热度排行Top40', '#000000', font, spacing=10)
    font = ImageFont.truetype(str(FONT_PATH / 'FOT-RodinNTLGPro-DB.ttf'), 18)
    draw.text((20, 53), text, '#000000', font, spacing=10)
    font = ImageFont.truetype(str(FONT_PATH / 'SourceHanSansCN-Medium.otf'), 15)
    updatetime = time.localtime(os.path.getmtime(data_path / r"realtime/musics.json"))
    draw.text((20, 1100), '数据来源：https://profile.pjsekai.moe/\nUpdated in '
              + time.strftime("%Y-%m-%d %H:%M:%S", updatetime), '#000000', font)
    await pjsk_hotrank.finish(image(b64=pic2b64(img)))
