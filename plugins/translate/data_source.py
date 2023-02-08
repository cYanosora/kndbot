import time
import random
import hashlib
from utils.http_utils import AsyncHttpx
try:
    import ujson as json
except:
    import json


# ZH_CN2EN 中文　»　英语
# ZH_CN2JA 中文　»　日语
# ZH_CN2KR 中文　»　韩语
# ZH_CN2FR 中文　»　法语
# ZH_CN2RU 中文　»　俄语
# ZH_CN2SP 中文　»　西语
# EN2ZH_CN 英语　»　中文
# JA2ZH_CN 日语　»　中文
# KR2ZH_CN 韩语　»　中文
# FR2ZH_CN 法语　»　中文
# RU2ZH_CN 俄语　»　中文
# SP2ZH_CN 西语　»　中文
# 中文: zh-CHS
# 英语: en
# 日语: ja
# 韩语: ko
# 法语: fr
# 德语: de
# 俄语: ru
# 西班牙语: es
# 葡萄牙语: pt
# 意大利语: it
# 越南语: vi
# 印尼语: id
# 阿拉伯语: ar
# 荷兰语: nl
# 泰语: th
def _parse_language(language_type: str):
    if language_type in ["翻译", "中翻", "翻中", "中文翻译", "翻译中文"]:
        return 'zh-CHS'
    if language_type in ["英翻", "翻英", "英文翻译", "翻译英文"]:
        return "en"
    if language_type in ["日翻", "翻日", "日文翻译", "翻译日文"]:
        return "ja"
    if language_type in ["韩翻", "翻韩", "韩文翻译", "翻译韩文"]:
        return "ko"
    if language_type in ["法翻", "翻法", "法文翻译", "翻译法文"]:
        return 'fr'
    if language_type in ["德翻", "翻德", "德文翻译", "翻译德文"]:
        return "de"
    if language_type in ["俄翻", "翻俄", "俄文翻译", "翻译俄文"]:
        return 'ru'
    return "zh-CHS"


async def translate_msg(cmd: str, text: str):
    lang = _parse_language(cmd)
    result = _translate_youdao(text, lang)
    if result:
        return result
    return "翻译失败惹.."


async def _translate_youdao(text: str, lang: str) -> str:
    """
    使用有道翻译文本为目标语言
    """
    url = f"https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        "Cookie": "OUTFOX_SEARCH_USER_ID=467129664@10.169.0.102; JSESSIONID=aaaejjt9lMzrAgeDsHrWx;OUTFOX_SEARCH_USER_ID_NCOO=1850118475.9388125; ___rl__test__cookies=1632381536261",
        "Referer": "https://fanyi.youdao.com/"
    }
    ts = str(int(time.time() * 1000))
    salt = ts + str(random.randint(0, 9))
    temp = "fanyideskweb" + text + salt + "Ygy_4c=r#e#4EX^NUGUc5"
    md5 = hashlib.md5()
    md5.update(temp.encode())
    sign = md5.hexdigest()
    data = {
        "i": text,
        "from": "Auto",
        "to": lang,
        "smartresult": "dict",
        "client": "fanyideskweb",
        "salt": salt,
        "sign": sign,
        "lts": ts,
        "bv": "5f70acd84d315e3a3e7e05f2a4744dfa",
        "doctype": "json",
        "version": "2.1",
        "keyfrom": "fanyi.web",
        "action": "FY_BY_REALTlME",
    }
    try:
        resp = await AsyncHttpx.post(url, data=data, headers=headers)
        result = json.loads(resp.content)
        res = ""
        for s in result['translateResult'][0]:
            res += s['tgt']
        return res
    except:
        return ""

