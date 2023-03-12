from configs.path_config import IMAGE_PATH

pjsk_path = IMAGE_PATH / "image_management" / "pjsk"

# key为分类文件夹名，value为key文件夹下的第二级文件夹，用于本地搜图
pjsk_info_dict = {
    "25h": ["knd", "mfy", "ena", "mzk"],
    "vbs": ["khn", "an", "akt", "toya"],
    "mmj": ["mnr", "hrk", "airi", "szk"],
    "ln": ["ick", "saki", "hnm", "shiho"],
    "ws": ["tks", "emu", "nene", "rui"],
    "vs": ["miku", "rin", "len", "luka", "meiko", "kaito"],
    "cp": [
        "knhn", "ickn", "mfem", "mzan", "other", "钢琴组",
        "姐弟", "姐妹", "类瑞", "兄妹", "mfsz", "enar", "anhr", "skty", "nety"
    ]
}

pjsk_cp_dict = {
    "25h": ["knen", "knmf", "mzkn", "mfen", "mfmz", "mzen"],
    "vbs": ["anak", "akkh", "akty", "ankh", "anty", "tykh"],
    "mmj": ["armn", "hrar", "hrmn", "hrsz", "szar", "szmn"],
    "ln": ["ichn", "icsh", "icsk", "shhn", "skhn", "sksh"],
    "ws": ["nemu", "ruiem", "ruine", "ruitk", "tkem", "tkne"],
}

# key为分类文件夹名，value为默认全局称呼，数据用于存入数据库以及info功能
pjsk_info_mapping = {
    "25h":"25时，在Night Code。","knd":"宵崎奏","mfy":"朝比奈真冬","ena":"东云绘名","mzk":"晓山瑞希",
    "vbs":"Vivid BAD SQUAD","khn":"小豆泽心羽","an":"白石杏","akt":"东云彰人","toya":"青柳冬弥",
    "mmj":"MORE MORE JUMP！","mnr":"花里实乃理","hrk":"桐谷遥","airi":"桃井爱莉","szk":"日野森雫",
    "ln":"Leo/need","ick":"星乃一歌","saki":"天马咲希","hnm":"望月穗波","shiho":"日野森志步",
    "ws":"Wonderlands × Showtime","tks":"天马司","emu":"凤绘梦","nene":"草薙宁宁",'rui':"神代类",
    "vs":"虚拟歌手","miku":"初音未来","rin":"镜音铃","len":"镜音连","luka":"巡音流歌","meiko":"MEIKO","kaito":"KAITO",
    "other":"杂图","姐弟":"东云姐弟","兄妹":"天马兄妹","姐妹":"日野森姐妹", "mzan": "瑞杏", "enar": "闺蜜组",
    "类瑞": "天台组","mfem":"真冬凤","钢琴组":"钢琴", "knhn": "奏穗", "ickn": "头发组", "mfsz": "弓道组",
    "anhr": "安遥", "nety": "冬宁", "skty": "冬咲",
    "knen": "奏绘", "knmf": "宵朝", "mzkn": "奏瑞", "mfen": "朝绘", "mfmz": "朝瑞", "mzen": "绘瑞",
    "anak": "彰杏", "akkh": "彰豆", "akty": "彰冬", "ankh": "杏豆", "anty": "冬杏", "tykh": "冬豆",
    "armn": "爱实", "hrar": "遥爱", "hrmn": "遥实", "hrsz": "遥雫", "szar": "爱雫", "szmn": "雫实",
    "ichn": "一穗", "icsh": "一志", "icsk": "一咲", "shhn": "志穗", "skhn": "咲穗", "sksh": "咲志",
    "nemu": "宁姆", "ruiem": "类姆", "ruine": "类宁", "ruitk": "类司", "tkem": "司姆", "tkne": "司宁",
}
# 组合名、角色名、cp名全部包括在内
pjsk_info_all = [chara for charas in pjsk_info_dict.values() for chara in charas] +\
                [unit for unit in pjsk_info_dict.keys()] +\
                [cp for cps in pjsk_cp_dict.values() for cp in cps]
pjsk_info_all.sort(key=len, reverse=True)

cpmap = {
    "knen": "knd×ena", "knmf": "knd×mfy", "mzkn": "knd×mzk", "mfen": "mfy×ena", "mfmz": "mfy×mzk", "mzen": "ena×mzk",
    "anak": "an×akt", "akkh": "khn×akt", "akty": "akt×toya", "ankh": "khn×an", "anty": "an×toya", "tykh": "khn×toya",
    "armn": "mnr×airi", "hrar": "hrk×airi", "hrmn": "mnr×hrk", "hrsz": "hrk×szk", "szar": "szk×airi", "szmn": "mnr×szk",
    "ichn": "ick×hnm", "icsh": "ick×shiho", "icsk": "ick×saki", "shhn": "shiho×hnm", "skhn": "saki×hnm", "sksh": "saki×shiho",
    "nemu": "emu×nene", "ruiem": "emu×rui", "ruine": "nene×rui", "ruitk": "tks×rui", "tkem": "tks×emu", "tkne": "tks×nene",
    "knhn": "hnm×knd", "mfem": "emu×mfy", "钢琴组": "saki×toya×tks", "姐弟": "akt×ena", "姐妹": "shiho×szk",
    "类瑞": "rui×mzk", "兄妹": "saki×tks", "ickn": "ick×knd", "mzan": "an×mzk", "mfsz":"szk×mfy", "enar": "airi×ena",
    "anhr": "hrk×an", "skty": "saki×toya", "nety": "toya×nene"
}