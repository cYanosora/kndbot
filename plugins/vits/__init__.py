import string
import asyncio
import traceback
from scipy.io.wavfile import write
from nonebot import on_message
from nonebot.adapters.onebot.v11 import GROUP, MessageSegment
from nonebot.exception import ActionFailed, NetworkError
from utils.limit_utils import ignore_cd, ignore_mute
from .depends import *
from .initial import *
from .config import *
from .utils import *
from .models import SynthesizerTrn
from .function import *
from .text.symbols import (
    symbols_ja,
    symbols_zh_CHS,
    symbols_pjsk1,
    symbols_pjsk2,
    symbols_pjsk3,
    symbols_pjsk4
)


__plugin_name__ = "VITS"
__plugin_type__ = "娱乐功能"
__plugin_version__ = 0.1
__plugin_usage__ = f"""
usage：
    使用VITS生成角色语音，因为服务器性能极其有限，故仅有部分开放高权限的群才可以使用
    指令：
        [角色名]说 [中文/日文]? [文字]
    举例：
        knd说こんニーゴ            : 输出日语语音
        kanade说日文よくわからない    : 输出日语语音
        小奏说日文我不是很懂         : 会先翻译为日文，再输出日语语音
        奏宝说中文你好，我是宵崎奏    : 输出协和语语音
        宵崎奏说中文ども、宵崎奏です    : 会先翻译为中文，再输出协和语语音
    注意：
        可识别的[角色名]为目前收录的烧烤原创角色(包括来自[角色昵称]功能中保存的角色别名)
        输出语音的语种仅支持中日双语，但无论你输入的[文字]本身是什么语种，最终生成的语音都会采用你选择的语言，默认为日文
        （意思就是会预先翻译你输入的文字为你所选择的语言）
        若语音生成失败，可以检查[文字]中的符号是否符合对应语种
        语音模型来自圈内大佬们，详请可参阅：https://github.com/Kanade-nya/PJSK-MultiGUI
        个人测评，感觉ws全员的效果可能不太好，然后志步的效果基本还挺好的(?)
        最后，请勿生成以及传播可能导致他人对角色产生严重误解的奇怪语音！
""".strip()
__plugin_settings__ = {
    "level": 6,
    "default_status": True,
    "cmd": ["VITS", "语音合成"],
}
__plugin_cd_limit__ = {"cd": 30, "count_limit": 3, "rst": "别急，等[cd]秒后再用！", "limit_type": "group"}
__plugin_block_limit__ = {"rst": "别急，还在生成！"}


symbols_dict = {
    "zh-CHS": symbols_zh_CHS,
    "ja": symbols_ja,
    "pjsk1": symbols_pjsk1,
    "pjsk2": symbols_pjsk2,
    "pjsk3": symbols_pjsk3,
    "pjsk4": symbols_pjsk4,
}

auto_delete_voice = plugin_config.auto_delete_voice if plugin_config.auto_delete_voice is not None else True
tts_gal = eval(plugin_config.tts_gal if plugin_config.tts_gal else '{():[""]}')
valid_names = []
driver = get_driver()


@driver.on_startup
def _():
    logger.info("正在检查目录是否存在...")
    asyncio.ensure_future(checkDir(base_path, voice_path))
    filenames = []
    [filenames.append(model[0])
     for model in tts_gal.values() if not model[0] in filenames]
    logger.info("正在检查配置文件是否存在...")
    asyncio.ensure_future(checkFile(model_path, config_path, filenames, tts_gal, valid_names))


voice = on_message(rule=checkRule(), permission=GROUP, block=True, priority=5)


@voice.handle()
async def voicHandler(
    event: GroupMessageEvent,
    name: str = RegexArg('name'),
    text: str = RegexArg('text'),
    type: str = RegexArg('type')
):
    global tts_gal
    global valid_names
    # 预处理
    config_file, model_file, index = check_character(name, valid_names, tts_gal)
    # 加载配置文件
    hps_ms = get_hparams_from_file(config_path / config_file)
    # 翻译的目标语言
    lang = load_language(hps_ms)
    symbols = load_symbols(hps_ms, lang, symbols_dict)
    # 目标语言再转化
    if lang.startswith('pjsk'):
        lang = 'ja'
    # 文本处理
    text = changeE2C(text) if lang == "zh-CHS" else changeC2E(text)
    if not text:
        await voice.finish('中文转换失败，请稍后再试')
    if type == '中文':
        text = await translate_youdao(text, 'zh-CHS')
        text = await translate_katakana(text)
        if lang != 'ja':
            text = await translate_youdao(text, lang)
    else:
        text = await translate_youdao(text, lang)
    if not text:
        await voice.finish('网络不太好，请稍后再试')
    text = get_text(text, hps_ms, symbols, lang, False)
    # 加载模型
    try:
        net_g_ms = SynthesizerTrn(
            len(symbols),
            hps_ms.data.filter_length // 2 + 1,
            hps_ms.train.segment_size // hps_ms.data.hop_length,
            n_speakers=hps_ms.data.n_speakers,
            **hps_ms.model)
        _ = net_g_ms.eval()
        load_checkpoint(model_path / model_file, net_g_ms)
    except:
        traceback.print_exc()
        limit = f"{event.group_id}_{event.user_id}"
        ignore_mute(limit)
        ignore_cd(limit,event)
        await voice.finish("加载模型失败")
        return
    # 随机文件名
    filename = "".join(random.sample([x for x in string.ascii_letters + string.digits], 8)) + ".wav"
    # 生成语音
    try:
        with no_grad():
            x_tst = text.unsqueeze(0)
            x_tst_lengths = LongTensor([text.size(0)])
            sid = LongTensor([index]) if index is not None else None
            audio = net_g_ms.infer(
                x_tst, x_tst_lengths, sid=sid, noise_scale=.667, noise_scale_w=0.8, length_scale=1
            )[0][0, 0].data.cpu().float().numpy()
        write(voice_path / filename, hps_ms.data.sampling_rate, audio)
    except:
        traceback.print_exc()
        limit = f"{event.group_id}_{event.user_id}"
        ignore_mute(limit)
        ignore_cd(limit,event)
        await voice.finish('生成失败')
        return
    # 发送语音
    try:
        await voice.send(MessageSegment.record(file=voice_path / filename))
    except ActionFailed:
        traceback.print_exc()
        limit = f"{event.group_id}_{event.user_id}"
        ignore_mute(limit)
        ignore_cd(limit,event)
        await voice.send("发送失败,请重试")
    except NetworkError:
        traceback.print_exc()
        limit = f"{event.group_id}_{event.user_id}"
        ignore_mute(limit)
        ignore_cd(limit,event)
        await voice.send("发送超时,也许等等就好了")
    finally:
        if auto_delete_voice:
            (voice_path / filename).unlink()


