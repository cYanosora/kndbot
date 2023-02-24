import json
from typing import Dict, Any
import msgpack
from nonebot import on_command, on_notice
from nonebot.adapters.onebot.v11 import MessageEvent, NoticeEvent, GroupMessageEvent
from configs.config import NICKNAME
from .rule import rule
from .._config import suite_path
from utils.http_utils import AsyncHttpx
from Crypto.Cipher import AES


__plugin_name__ = "上传用户信息/pjskupload"
__plugin_type__ = "烧烤相关&uni移植"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    由于日服api作了大幅修改，部分功能(pjskb30、pjsk进度)无法正常使用
    此功能的意义在于让部分有能力的用户恢复这些功能的使用
    说明：
        所谓的用户信息需要自己在游戏内获取并上传
        目前ios可参考uni的教程网站: https://docs.unipjsk.com/suite/
        android暂无教程，需要root安装证书后配合抓包软件，个人认为会root的基本抓包也不是难事
        为保障用户数据隐私，请与bot私聊触发指令
    指令：
        上传用户信息                  :在私聊内发送此指令后，请传输用户的文件
        pjskupload                  :同上
    举例：
        * 私聊内(需加bot好友) *
        You:上传用户信息
        Bot:请发送原始数据包文件
        You:[文件]
        Bot:识别成功，用户(此处为id)的信息已记录！
""".strip()
__plugin_settings__ = {
    "default_status": False,
    "cmd": ["pjskupload", "烧烤相关", "上传用户信息"],
}

# pjsk个人档案
pjsk_upload = on_command('pjskupload', aliases={"上传用户信息"}, priority=5, block=True)
pjsk_upload_file = on_notice(priority=1, rule=rule(), block=False)
pjsk_global_flag = False


@pjsk_upload.handle()
async def _(event: MessageEvent):
    global pjsk_global_flag
    if isinstance(event, GroupMessageEvent):
        await pjsk_upload.finish(f"请在私聊内使用此功能！私聊前请加{NICKNAME}好友~", at_sender=True)
    else:
        pjsk_global_flag = True
        await pjsk_upload.finish(f"请发送原始数据包文件")


# 私聊上传文件的消息，框架暂不支持，容易出各种错误，干脆使用基类处理
@pjsk_upload_file.handle()
async def _(event: NoticeEvent):
    global pjsk_global_flag
    if not pjsk_global_flag:
        return
    pjsk_global_flag = False
    if not isinstance(event, NoticeEvent):
        await pjsk_upload.finish("不要发送文件以外的消息，请重新触发指令")
    if event.notice_type != 'offline_file':
        await pjsk_upload.finish("识别失败，请重新发送离线文件")
    else:
        file_url = event.dict()['file']['url']
        if reply := await save_data(file_url):
            await pjsk_upload.finish(reply)
        else:
            await pjsk_upload.finish('出错了，可能是文件不符合要求！')


async def save_data(file_url: str) -> str:
    content = (await AsyncHttpx.get(file_url)).content

    def unpack(encrypted: bytes) -> Dict[str, Any]:
        mode = AES.MODE_CBC
        key = b"g2fcC0ZczN9MTJ61"
        iv = b"msx3IV0i9XE5uYZ1"
        cryptor = AES.new(key, mode, iv)
        plaintext = cryptor.decrypt(encrypted)
        return msgpack.unpackb(plaintext[:-plaintext[-1]], strict_map_key=False)
    try:
        _data = unpack(content)
        user_id = _data['user']['userRegistration']['userId']
        with open(suite_path / f'{user_id}.json', 'w', encoding='utf-8') as f:
            json.dump(_data, f)
        success_text = f'识别成功，用户({user_id})的信息已记录！'
    except:
        success_text = ''
    return success_text

