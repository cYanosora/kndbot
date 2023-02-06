from .functions import *
from .models import Command
from nonebot import get_driver

bot_nicknames = list(get_driver().config.nickname) + [" "]
nickstr="|".join(bot_nicknames)
tmp_ls = []
for i in pjsk_chara_dict.values():
    tmp_ls.extend(i)
charastr = "" + "|".join(tmp_ls)
tmp_ls.clear()

commands = [
    Command(1, "[^别不]*骂我[嘛|吧|叭]?$", curse_voice, need_at=True, next=True),
    Command(2, "[^别不]*(老婆|我爱你|我爱死你了|我喜欢你|踩|结婚|嫁给我).*", my_wife, priority=4, need_at=True, next=True),
    Command(3, ".*(可爱|卡瓦|kawa|kawaii|kawai|kwi|卡哇伊).*", knd_kawaii, need_at=True, next=True),
    Command(4, "^[嗦吃喝][泡杯]?面$", eat_noodles, need_at=True, next=True),
    Command(5, "^(早安|早上好|上午好|中午好|午安|下午好|晚上好|[咱我俺偶]要?去?睡觉?了"
               "|晚安|(1|25|二五|二十五)[点时](好|啦|辣|了|咯|叻|到了)|こんニーゴ)", knd_zwa, need_at=True, next=True),
    Command(6, "", poke_event, mode="ntc", next=True),
    Command(7, ".+", other_reactions, need_at=True, next=True, priority=8),
    Command(8, "^({})$".format(charastr), chara_perspective, need_at=False, next=True, priority=7),
    Command(9, "^(生日|诞生日|誕生日|)快乐|happy birthday", birthday, priority=4, need_at=True, next=True),
    Command(0, "^门[🙏🙏🙏🏻🙏🏼🙏🏽🙏🏾🙏🏿]?$", knd_men, need_at=True),
    Command(0, "^(爬|丢人爬|爪巴)$", pa_reg),
    Command(0, "^[{}]*[!！。.,，？?~><]*$".format(nickstr), knd_emoji, need_at=True),
    Command(0, "今日运势", jrrp, alias={"jrys", "幸运曲", "运势", "打歌运势"}, priority=6, mode="cmd"),
]

