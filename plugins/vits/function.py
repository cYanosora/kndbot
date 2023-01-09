import time
import httpx
import random
from lxml import etree
import hashlib
from torch import no_grad, LongTensor
from typing import Optional, Tuple, Dict, List
from utils.user_agent import get_user_agent
from .text import text_to_sequence
from .commons import intersperse
from .utils import *


def check_character(name, valid_names, tts_gal) -> Tuple[str, str, Optional[int]]:
    """
    检查角色是否存在
    """
    index = None
    config_file = ""
    model_file = ""
    for names, model in tts_gal.items():
        if names in valid_names and ((isinstance(names,str) and names == name) or name in names):
            config_file = model[0] + ".json"
            model_file = model[0] + ".pth"
            index = None if len(model) == 1 else int(model[1])
            break
    return config_file, model_file, index


def load_language(hps_ms):
    """
    读取配置文件的language设定项
    """
    try:
        return hps_ms.language
    except:
        return "ja"


def load_symbols(hps_ms: HParams, lang: str, symbols_dict: Dict) -> List:
    """
    读取配置文件的symbols设定项
    """
    try:
        symbols = hps_ms.symbols
    except:
        if lang in symbols_dict.keys():
            symbols = symbols_dict[lang]
        else:
            symbols = symbols_dict["ja"]
    return symbols


def get_text(text: str, hps: HParams, symbols: List, lang: str, cleaned=False):
    """
    转化文本为LongTensor
    """
    if cleaned:
        text_norm = text_to_sequence(text, symbols, [], lang)
    else:
        text_norm = text_to_sequence(
            text, symbols, hps.data.text_cleaners, lang)
    if hps.data.add_blank:
        text_norm = intersperse(text_norm, 0)
    text_norm = LongTensor(text_norm)
    return text_norm


def changeC2E(s: str):
    """
    中文符号转英文符号
    """
    return s.replace("。", ".").replace("？", "?").replace("！", "!").replace("，", ",")


def changeE2C(s: str):
    """
    英文符号转中文符号
    """
    return s.replace(".", "。").replace("?", "？").replace("!", "！").replace(",", "，")


async def translate_katakana(text: str) -> str:
    """
    中文转片假名
    """
    url = "https://www.chineseconverter.com/zh-cn/convert/chinese-characters-to-katakana-conversion"
    headers = get_user_agent()
    headers['Referer'] = 'https://www.chineseconverter.com/'
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            tree = etree.HTML(resp.content)
            csrf = tree.xpath("//input[@name='_csrf-frontend']/@value")[0]
            form_data = {
                "ChineseToKatakana[input]": text,
                "ChineseToKatakana[type]": "pinyin",
                "ChineseToKatakana[languageType]": "hiragana",
                "_csrf-frontend": csrf
            }
            resp = await client.post(url, data=form_data, headers=headers)
            tree = etree.HTML(resp.content)
            result = tree.xpath('//*[@id="w0"]//div[contains(@class,"thumbnail")]/text()')[0]
            return result.strip()
    except:
        return ''


async def translate_youdao(text: str, lang: str) -> str:
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
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data, headers=headers)
            result = json.loads(resp.content)
        res = ""
        for s in result['translateResult'][0]:
            res += s['tgt']
        return res
    except:
        return ""


