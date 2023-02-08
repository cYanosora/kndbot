import random
import secrets
import time
from datetime import datetime
from typing import Dict, Tuple
from basic_plugins.shop.shop_handle import register_goods
from basic_plugins.shop.use import register_use
from configs.path_config import DATA_PATH
from models.group_member_info import GroupInfoUser
from utils.imageutils import text2image, pic2b64
from utils.message_builder import image
from utils.utils import scheduler
from services.log import logger
from nonebot import Driver, require
import nonebot
from models.sign_group_user import SignGroupUser
from models.bag_user import BagUser
from models.goods_info import GoodsInfo
try:
    import ujson as json
except:
    import json
__plugin_name__ = "商店定时任务 [Hidden]"
__plugin_version__ = 0.1
driver: Driver = nonebot.get_driver()
gift_data = {}

# 重置每日金币
@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=0,
)
async def _():
    try:
        user_list = await BagUser.get_all_users()
        for user in user_list:
            await user.update(
                get_today_gold=0,
                spend_today_gold=0,
            ).apply()
    except Exception as e:
        logger.error(f"重置每日金币错误 e:{e}")


# 重置商品限购次数
@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=0,
)
async def _():
    try:
        await GoodsInfo.reset_daily_purchase()
        logger.info("商品每日限购次数重置成功...")
    except Exception as e:
        logger.error(f"商品每日限购次数重置发生错误 {type(e)}：{e}")


# 每日随机商品打折
@scheduler.scheduled_job(
    "interval",
    start_date=datetime(2023, 2, 10, 0, 0, 0),
    days=1
)
async def _():
    try:
        all_goods = list(filter(
            lambda good:good.goods_limit_time == 0 and good.is_show and not good.is_passive,
            await GoodsInfo.get_all_goods()
        ))
        # 重置商店折扣道具
        for good in all_goods:
            if good.goods_discount != 1:
                await GoodsInfo.update_goods(good.goods_name,goods_discount=1)
        # 随机非限时的已展示的主动道具打折
        good = random.choice(all_goods)
        await GoodsInfo.update_goods(good.goods_name,goods_discount=0.9)
    except Exception as e:
        logger.error(f"每日随机折扣道具失败 e:{e}")


# 2月9日22时发放全员生日礼物
@scheduler.scheduled_job(
    'date',
    run_date=datetime(2023, 2, 9, 22, 0, 0),
)
async def _():
    global gift_data
    bots = list(nonebot.get_bots().values())
    all_groups = []
    for bot in bots:
        gl = await bot.get_group_list()
        gl = [g["group_id"] for g in gl]
        all_groups.extend(gl.copy())
    all_groups = list(set(all_groups))
    type_groups = []
    for group in all_groups:
        group = int(group)
        totalday = 1
        for bot in bots:
            botinfo = await GroupInfoUser.get_member_info(int(bot.self_id), group)
            if not botinfo:
                continue
            join_group_time = botinfo.user_join_time.date()
            totalday = (datetime.now().date() - join_group_time).days + 1
        type_groups.append((group, totalday))
    for groupinfo in type_groups:
        gift_data[groupinfo[0]] = {'days':groupinfo[1],'users':[]}
        allsignusers = await SignGroupUser.get_all_users(groupinfo[0])
        allsignusers.sort(key=lambda signuser: signuser.impression, reverse=True)
        allsignusers.sort(key=lambda signuser: signuser.checkin_count, reverse=True)
        if groupinfo[1] > 60:
            for _id, signuser in enumerate(allsignusers):
                if signuser.checkin_count == 0:
                    continue
                gift = '无'
                _t = '无'
                if _id < len(allsignusers) * 0.1 and signuser.checkin_count / groupinfo[1] >= 0.75:
                    gift = '生日礼物2'
                    _t = '漏签少排名高'
                elif signuser.checkin_count >= 100:
                    gift = '生日礼物2'
                    _t = '天数多'
                elif signuser.impression >= 25:
                    gift = '生日礼物1'
                    _t = '好感高'
                gift_data[groupinfo[0]]['users'].append({
                    'qq':str(signuser.user_qq),
                    'signdays':signuser.checkin_count,
                    'impr':signuser.impression,
                    'rank':_id+1,
                    'gift':gift
                })
                if gift != '无':
                    await BagUser.add_property(signuser.user_qq, signuser.group_id, gift, max=1)
                logger.info(f'User{signuser.user_qq}({_t}) Group{signuser.group_id}(天数{groupinfo[1]}) 获得礼物 {gift}')
        else:
            for _id, signuser in enumerate(allsignusers):
                if signuser.checkin_count == 0:
                    continue
                gift = '无'
                _t = '无'
                if signuser.checkin_count >= 100:
                    gift = '生日礼物2'
                    _t = '天数多'
                elif signuser.impression >= 25:
                    gift = '生日礼物1'
                    _t = '好感高'
                gift_data[groupinfo[0]]['users'].append({
                    'qq':str(signuser.user_qq),
                    'signdays':signuser.checkin_count,
                    'impr':signuser.impression,
                    'rank':_id+1,
                    'gift':gift
                })
                if gift != '无':
                    await BagUser.add_property(signuser.user_qq, signuser.group_id, gift, max=1)
                logger.info(f'User{signuser.user_qq}({_t}) Group{signuser.group_id}(天数{groupinfo[1]}) 获得礼物 {gift}')
    with open(DATA_PATH / 'limit_event.json', 'w', encoding='utf-8') as f:
        json.dump(gift_data,f)
    logger.info(f'保存数据成功')


# 注册新被动道具
@driver.on_startup
async def _():
    require('sign_in')
    require('random_reply')
    from basic_plugins.random_reply import ReplyBank, UserInfo, retry_manager
    # 注册生日礼物1&2、康乃馨、合成器、八音盒
    data = {
        '生日礼物1':{
            'price': -1,
            'des':"今天是奏宝的生日，这是你打算送给奏宝的生日礼物，奏宝收到后会有什么感受呢？",
            'effect':'随机得到奏宝的感谢语+奖励',
            'discount':1,
            'limit_time':0,
            'daily_limit':0,
            'is_passive':False,
            'is_show':False,
            'icon':'gift1.png'
        },
        '生日礼物2': {
            'price': -1,
            'des': "你和奏宝相处甚久，这是你精心送给奏宝的生日礼物，奏宝收到后会有什么感受呢？",
            'effect': '随机得到奏宝的感谢语+奖励+纪念品',
            'discount': 1,
            'limit_time': 0,
            'daily_limit': 0,
            'is_passive': False,
            'is_show': False,
            'icon': 'gift2.png'
        },
        '康乃馨': {
            'price': -1,
            'des': "这是奏母最喜爱的花，寄宿着奏过去那弥足珍贵的温暖回忆",
            'effect': '(康乃馨样本)签到获取好感永久 + 6%',
            'discount': 1,
            'limit_time': 0,
            'daily_limit': 0,
            'is_passive': True,
            'is_show': False,
            'icon': 'souvenir1.png'
        },
        '八音盒': {
            'price': -1,
            'des': "这是奏父制作的八音盒，播放的时候仿佛给人以包容一切的温柔与安心感",
            'effect': '(八音盒样本)签到获取金币永久 + 25%',
            'discount': 1,
            'limit_time': 0,
            'daily_limit': 0,
            'is_passive': True,
            'is_show': False,
            'icon': 'souvenir2.png'
        },
        '合成器': {
            'price': -1,
            'des': "奏用来作曲的工具，记录着奏多年来作曲的成长",
            'effect': '(合成器样本)购买商店道具享受 20% 折扣',
            'discount': 1,
            'limit_time': 0,
            'daily_limit': 0,
            'is_passive': True,
            'is_show': False,
            'icon': 'souvenir3.png'
        },
        '乐谱': {
            'price': 2525,
            'des': "奏平日里写出来的乐谱，虽然完成度很高但被散乱地放置在地上，帮助奏找回的话究竟会怎样呢",
            'effect': '好感立即+2.5，之后三天内签到好感×2，期间好感双倍卡将失效并返还',
            'discount': 1,
            'limit_time': 0,
            'daily_limit': 0,
            'is_passive': False,
            'is_show': False,
            'icon': 'music.png'
        }
    }
    for name in data.keys():
        await register_goods(
            name,
            data[name]["price"],
            data[name]["des"],
            data[name]["effect"],
            data[name]["discount"],
            data[name]["limit_time"],
            data[name]["daily_limit"],
            data[name]["is_passive"],
            data[name]["is_show"],
            data[name]["icon"],
        )
        logger.info(f'纪念品 {name} 道具添加完毕')

    async def func1(user_id: int, group_id: int, goods_name: str):
        nowdate = datetime.now()
        if (
                (nowdate.month == 2 and nowdate.day == 10) or
                (nowdate.month == 2 and nowdate.day == 9 and nowdate.hour == 23)
        ):
            reply_ls = []
            # 加好感、金币、道具
            impression, gold, items = random_gift()
            # 添加默认回复
            reply = '好感+{:.2f}，金币+{}\n获得道具:'.format(impression, gold)
            for i, j in items.items():
                reply += "{} × {}，".format(i, j)
            reply = reply[:-1]
            reply_ls.append(image(b64=pic2b64(text2image(reply))))
            # 触发对话
            userinfo = UserInfo(
                qq=user_id,
                group=group_id,
                text="",
                state=0,
                cid=9
            )
            reply, state = await ReplyBank.get_user_mutil_reply(9, 'gift1_0', userinfo, 0.5, 0.5, True)
            if state != 0:
                retry_manager.add(user_id, group_id, 9, state)
            if isinstance(reply, str):
                fin_msg = await ReplyBank.get_final_reply_list(reply)
            else:
                fin_msg = [reply]
            for i in fin_msg:
                reply_ls.append(i)
            # 加好感、金币、签到道具
            signuser = await SignGroupUser.ensure(user_id, group_id)
            await signuser.update(
                impression=signuser.impression + impression,
            ).apply()
            await BagUser.add_gold(user_id, group_id, gold)
            for item in items.keys():
                await BagUser.add_property(user_id, group_id, item, items[item])
            return reply_ls
        elif (
                nowdate.month > 2 or
                (nowdate.month == 2 and nowdate.day > 10)
        ):
            await BagUser.add_property(user_id, group_id, goods_name, 1)
            return "残念~ 生日已经过了，这个道具就只能自己留作纪念了"
        else:
            await BagUser.add_property(user_id, group_id, goods_name, 1)
            return '现在还没有到送出生日礼物的时机哦？'

    async def func2(user_id: int, group_id: int, goods_name: str, text: str):
        nowdate = datetime.now()
        if (
            (nowdate.month == 2 and nowdate.day == 10) or
            (nowdate.month == 2 and nowdate.day == 9 and nowdate.hour == 23)
        ):
            # 兑换道具
            goods = ['康乃馨', '八音盒', '合成器']
            for good in goods:
                if good in text:
                    reply_ls = []
                    reply = ''
                    # 加好感、金币、道具
                    impression, gold, items = random_gift()
                    reply += '好感+{:.2f}，金币+{}\n获得道具:'.format(impression, gold)
                    for i, j in items.items():
                        reply += "{} × {}，".format(i, j)
                    reply = reply[:-1] + f"\n获得纪念品道具{good}"
                    reply_ls.append(image(b64=pic2b64(text2image(reply))))
                    userinfo = UserInfo(
                        qq=user_id,
                        group=group_id,
                        text="",
                        state=0,
                        cid=9
                    )
                    # 触发对话
                    _reply_type = {'康乃馨':'gift2_1','八音盒':'gift2_2','合成器':'gift2_3'}.get(good)
                    reply, state = await ReplyBank.get_user_mutil_reply(9, _reply_type, userinfo, 0.5, 0.5, True)
                    if state != 0:
                        retry_manager.add(user_id, group_id, 9, state)
                    if isinstance(reply, str):
                        fin_msg = await ReplyBank.get_final_reply_list(reply)
                    else:
                        fin_msg = [reply]
                    for i in fin_msg:
                        reply_ls.append(i)
                    # 送纪念品道具
                    await BagUser.add_property(user_id,group_id,good,1)
                    # 加好感、金币、签到道具
                    signuser = await SignGroupUser.ensure(user_id,group_id)
                    await signuser.update(
                        impression=signuser.impression + impression,
                    ).apply()
                    await BagUser.add_gold(user_id,group_id,gold)
                    for item in items.keys():
                        await BagUser.add_property(user_id,group_id,item,items[item])
                    break
            else:
                reply_ls = "请输入需要兑换的道具。举例：使用生日礼物2兑换康乃馨"
                await BagUser.add_property(user_id, group_id, goods_name, 1)
            return reply_ls
        elif(
            nowdate.month > 2 or
            (nowdate.month == 2 and nowdate.day > 10)
        ):
            await BagUser.add_property(user_id, group_id, goods_name, 1)
            return "残念~ 生日已经过了，这个道具就只能自己留作纪念了"
        else:
            await BagUser.add_property(user_id, group_id, goods_name,1)
            return '现在还没有到送出生日礼物的时机哦？'

    async def func3(user_id: int, group_id: int):
        reply = ['家里这么乱，能帮我找到这张乐谱真是辛苦你了(❁´◡`❁)', random.choice([
            '...虽然是过去写一半就废弃的乐谱了，但现在的话，意外地产生了能接着写的灵感',
            '...话说这是什么时候作的乐谱？基调还行，但感觉一些地方还能更加有创意些，总之试着来完善这曲吧',
            '...(奏哼着旋律♪~)啊，某非这是我以前模仿着父亲的曲子作的嘛？虽然还很不成熟但好怀念啊——'
        ])]
        impr = 2.5
        signuser = await SignGroupUser.ensure(user_id, group_id)
        impression = signuser.impression + impr
        await signuser.update(impression=impression).apply()
        await SignGroupUser.add_property(user_id, group_id, '乐谱', num=3, disposable=False)
        return reply
    # 注册生日礼物1&2的使用函数
    register_use('生日礼物1', func1, **{})
    register_use('生日礼物2', func2, **{})
    register_use('乐谱', func3, **{})
    logger.info('生日礼物、乐谱道具的使用函数注册完毕')


# 2月9日23时开放限时道具展示
@scheduler.scheduled_job(
    'date',
    run_date=datetime(2023, 2, 9, 23, 0, 0),
)
async def _():
    goods = ['康乃馨', '八音盒', '合成器', '乐谱']
    for name in goods:
        await GoodsInfo.update_goods(name, is_show=True)
    logger.info('开放纪念品道具展示成功')


# 2月10日0时乐谱道具限时7天出售
@scheduler.scheduled_job(
    'date',
    run_date=datetime(2023, 2, 9, 23, 0, 0),
)
async def _():
    limit_time = int(time.time()) + 7 * 86400 + 3600
    await GoodsInfo.update_goods('乐谱', is_show=True, goods_limit_time=limit_time)
    logger.info('开放限时道具展示成功')


def random_gift() -> Tuple[float, int, Dict[str, int]]:
    base_impr = 0.5
    base_gold = 50
    base_item = {'杯面':1}
    base_impr += (secrets.randbelow(99) + 1) / 100
    base_gold += secrets.randbelow(99)
    rd = (secrets.randbelow(99) + 1) / 100
    if rd < 0.025:
        base_item['补签卡'] = 1
    elif rd < 0.05:
        base_item['好感双倍卡3'] = 1
    elif rd < 0.09:
        base_item['好感双倍卡2'] = 1
    elif rd < 0.2:
        base_item['好感双倍卡1'] = 1
    return base_impr, base_gold, base_item
