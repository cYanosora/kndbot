import psutil
import time
from datetime import datetime
from utils.http_utils import AsyncHttpx
from utils.imageutils import BuildImage as IMG, Text2Image
from configs.path_config import IMAGE_PATH
import asyncio
from services.log import logger


class Check:
    def __init__(self):
        self.cpu = None
        self.memory = None
        self.disk = None
        self.user = None
        self.baidu = 200
        self.google = 200

    async def check_all(self):
        await self.check_network()
        await asyncio.sleep(0.1)
        self.check_system()
        self.check_user()

    def check_system(self):
        self.cpu = psutil.cpu_percent()
        self.memory = psutil.virtual_memory().percent
        self.disk = psutil.disk_usage("/").percent

    async def check_network(self):
        try:
            await AsyncHttpx.get("https://www.baidu.com/", timeout=5)
        except Exception as e:
            logger.warning(f"访问BaiDu失败... {type(e)}: {e}")
            self.baidu = 404
        try:
            await AsyncHttpx.get("https://www.google.com/", timeout=5)
        except Exception as e:
            logger.warning(f"访问Google失败... {type(e)}: {e}")
            self.google = 404

    def check_user(self):
        rst = ""
        for user in psutil.users():
            rst += f'[{user.name}] {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(user.started))}\n'
        self.user = rst[:-1]

    async def show(self):
        await self.check_all()
        rst = (
            f'[Time] {str(datetime.now()).split(".")[0]}\n'
            f"-----System-----\n"
            f"[CPU] {self.cpu}%\n"
            f"[Memory] {self.memory}%\n"
            f"[Disk] {self.disk}%\n"
            f"-----Network-----\n"
            f"[BaiDu] {self.baidu}\n"
            f"[Google] {self.google}\n"
        )
        if self.user:
            rst += "-----User-----\n" + self.user
        textimg = Text2Image.from_text(rst, fontsize=24, fontname="PingFang SC.ttf", ischeckchar=False).to_image()
        width, height = textimg.size
        bk = IMG.open(IMAGE_PATH / "background" / "check" / "0.jpg")
        scale = bk.width / bk.height
        width, height = max(int(height * scale), width), max(int(width / scale), height)
        bk = bk.resize((width, height))
        bk.filter("GaussianBlur", 10)
        bk.paste(textimg, alpha=True, center_type='center')
        return bk.pic2bs4()
