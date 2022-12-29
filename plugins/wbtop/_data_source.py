from nonebot.adapters.onebot.v11 import MessageSegment
from utils.imageutils import BuildImage as IMG, Text2Image
from utils.message_builder import image
from configs.path_config import IMAGE_PATH
from typing import Tuple, Union
from utils.http_utils import AsyncHttpx
import datetime


async def get_wbtop(url: str) -> Tuple[Union[dict, str], int]:
    """
    :param url: 请求链接
    """
    n = 0
    while True:
        try:
            data = []
            get_response = (await AsyncHttpx.get(url, timeout=20))
            if get_response.status_code == 200:
                data_json = get_response.json()['data']['realtime']
                for data_item in data_json:
                    # 如果是广告，则不添加
                    if 'is_ad' in data_item:
                        continue
                    dic = {
                        'hot_word': data_item['note'],
                        'hot_word_num': str(data_item['num']),
                        'url': 'https://s.weibo.com/weibo?q=%23' + data_item['word'] + '%23',
                    }
                    data.append(dic)
                if not data:
                    return "没有搜索到...", 997
                return {'data': data, 'time': datetime.datetime.now()}, 200
            else:
                if n > 2:
                    return f'获取失败,请十分钟后再试', 999
                else:
                    n += 1
                    continue
        except TimeoutError:
            return "超时了....", 998


def gen_wbtop_pic(data: dict) -> MessageSegment:
    """
    生成微博热搜图片
    :param data: 微博热搜数据
    """
    bk = IMG.new("RGB", (700, 32 * 50 + 280), color="white")  # color="#797979"
    wbtop_bk = IMG.open(IMAGE_PATH / "other" / "webtop.png").resize((700, 280))
    bk.paste(wbtop_bk)
    text_bk = IMG.new("RGBA", (700, 32 * 50), color="#797979")
    for i, data in enumerate(data):
        title = f"{i + 1}. {data['hot_word']}"
        hot = data["hot_word_num"]
        img = IMG.new("RGB", (700, 30), color="white")
        fontname = "SourceHanSansCN-Regular.otf"
        title_img = Text2Image.from_text(title, fontsize=20, fontname=fontname, ischeckchar=False).to_image()
        hot_img = Text2Image.from_text(hot, fontsize=20, fontname=fontname, ischeckchar=False).to_image()
        w, h = title_img.size
        img.paste(title_img, (10, int((30 - h) / 2)), alpha=True)
        img.paste(hot_img, (580, int((30 - h) / 2)), alpha=True)
        text_bk.paste(img, (0, 32 * i))
    bk.paste(text_bk, (0, 280))
    return image(b64=bk.pic2bs4())