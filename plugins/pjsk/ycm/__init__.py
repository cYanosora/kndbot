import lxml.etree
from pathlib import Path
from typing import Dict, List
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GROUP
from services import logger
from nonebot_plugin_htmlrender import template_to_pic
from utils.http_utils import AsyncHttpx
from utils.message_builder import image

__plugin_name__ = "烧烤推车查询"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    获取烧烤最近的推车，限制每个群1分钟只能使用2次
    指令：
        ycm/车来/有车吗/推车
    两个好用的烧烤推车网站：
        城城的推车Station：http://59.110.175.37:5000/
        纹月的推车Station：http://1.117.147.194:8459/
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["烧烤推车查询", "ycm", "烧烤相关", "uni移植"],
}
__plugin_block_limit__ = {"rst": "别急，正在寻找推车中",}
__plugin_cd_limit__ = {
    "cd": 60,
    "limit_type": "group",
    "count_limit": 2,
    "rst": "别急，[cd]s后再用！"
}

# pjsk查推车
ycm = on_command('ycm', aliases={"车来", "有车吗", "推车"}, permission=GROUP, priority=5, block=True)


@ycm.handle()
async def _():
    await ycm.send('请稍后，正在获取推车中...', at_sender=True)
    cars = await get_cars_wy()
    if not cars:
        cars = await get_cars_cc()
    try:
        pic = await render_reply(cars)
        await ycm.send(image(pic))
    except Exception as e:
        logger.warning(f"生成网页图片发生错误： {e}")
        await ycm.finish(
            "出错了，建议直接戳网址：\n"
            "http://1.117.147.194:8459/\n"
            "http://59.110.175.37:5000/"
        )


async def get_cars_wy() -> List:
    try:
        url = 'http://1.117.147.194:8459/'
        html = (await AsyncHttpx.get(url, timeout=4)).text
        xp = '/html/body//div[@class="item"]'
        trees = lxml.etree.HTML(html).xpath(xp)
        car = {}
        cars = []
        for tree in trees:
            car['room'] = tree.xpath('./h3/text()')[0]
            car['des'] = '\n'.join(tree.xpath('./div/text()'))
            car['time'] = tree.xpath('./h5/text()')[0]
            cars.append(car.copy())
    except Exception as e:
        logger.warning(f"获取纹月推车发生错误： {e}")
        return []
    else:
        return cars


async def get_cars_cc() -> List:
    try:
        url = 'http://59.110.175.37:5000/'
        # 获取车站数据
        html = (await AsyncHttpx.get(url, timeout=4)).text
        # 解析数据
        tree = lxml.etree.HTML(html)
        xp = '/html/body/div/table//td/text()'
        result = tree.xpath(xp)
        # 重新封装数据，制作网页截图
        car = {}
        cars = []
        for index, each in enumerate(result):
            if index % 4 == 0:
                pass
            elif index % 4 == 1:
                car['room'] = each
            elif index % 4 == 2:
                car['des'] = each
            elif index % 4 == 3:
                car['time'] = each
                cars.append(car.copy())
                car.clear()
    except Exception as e:
        logger.warning(f"获取城城推车发生错误： {e}")
        return []
    else:
        return cars


async def render_reply(cars: List[Dict[str, str]]) -> bytes:
    if not cars:
        raise Exception('没有找到车！建议检查网页结构是否变化')
    template_path = str(Path(__file__).parent / "templates")
    template_name = "ycm.html"
    return await template_to_pic(
        template_path=template_path,
        template_name=template_name,
        templates={"cars": cars},
        pages={
            "viewport": {"width": 1180, "height": 300},
            "base_url": f"file://{template_path}",
        },
        wait=0,
    )
