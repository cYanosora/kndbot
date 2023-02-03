import nonebot
from nonebot import Driver
from nonebot.plugin import require
from datetime import datetime, timedelta
from typing import Callable, Tuple, Union
from manager import Config
from models.bag_user import BagUser
from models.sign_group_user import SignGroupUser

driver: Driver = nonebot.get_driver()

__plugin_name__ = "商品使用函数注册 [Hidden]"
__plugin_version__ = 0.1


# 导入默认道具(包括加入数据库、注册三种使用函数)
@driver.on_startup
async def _():
    if Config.get_config('shop', 'IMPORT_DEFAULT_SHOP_GOODS'):
        await init_default_shop_goods()


# 一次性注册道具使用函数
@driver.on_bot_connect
async def _():
    await shop_register.load_register()


async def init_default_shop_goods():
    """
    导入内置的六个商品
    """

    @shop_register(
        name=("好感双倍卡1", "好感双倍卡2", "好感双倍卡3", "好感双倍卡max"),
        price=(100, 180, 250, 700),
        des=(
            "蕴含某种力量的卡，貌似数量越多效果越好",
            "这些卡总有种很眼熟的感觉",
            "这些卡究竟有什么魔力，居然可以提升他人的好感",
            "量变产生质变"
        ),
        effect=(
            "下一次签到双倍好感触发概率 + 10%",
            "下一次签到双倍好感触发概率 + 20%",
            "下一次签到双倍好感触发概率 + 30%",
            "下一次签到必定触发双倍好感"
        ),
        load_status=True,
        daily_limit=0,
        is_passive=False,
        is_show=True,
        icon=("signcard1.png", "signcard2.png", "signcard3.png", "signcard4.png"),
        ** {"好感双倍卡1_prob": 0.1,"好感双倍卡2_prob": 0.2,"好感双倍卡3_prob": 0.3,"好感双倍卡max_prob": 1},
    )
    async def sign_card(user_id: int, group_id: int, prob: float, goods_name: str):
        user = await SignGroupUser.ensure(user_id, group_id, True)
        old_sign_items = [i for i in user.sign_items.keys() if i.startswith("好感双倍卡")]
        if old_sign_items:
            old_sign_items = old_sign_items[0]
            new_sign_items = user.sign_items
            new_sign_items[goods_name] = new_sign_items.pop(old_sign_items)
            await user.update(add_probability=prob, sign_items=new_sign_items).apply()
            await BagUser.add_property(user_id, group_id, old_sign_items)
            if goods_name == old_sign_items:
                reply = f"你已经使用过同名道具了噢？"
            else:
                reply = f"你使用 {goods_name} 覆盖了当前道具 {old_sign_items} 的加成效果！原道具归还给你咯..."
            return reply
        else:
            await user.update(add_probability=prob).apply()
            await SignGroupUser.add_property(user_id, group_id, goods_name)

    @shop_register(
        name="杯面",
        price=100,
        des="奏宝最爱的食品，无论哪种口味都吃不腻",
        effect="下一次签到时获得额外好感度，使用3次临时提高好感度等级",
        load_status=True,
        daily_limit=0,
        is_passive=False,
        is_show=True,
        icon="cupnoodle.png",
        **{"max_num_limit": 3}
    )
    async def cup_noodle(user_id: int, group_id: int, goods_name: str, max_num_limit: int, num: int):
        user = await SignGroupUser.ensure(user_id, group_id)
        # 已使用的道具次数
        cup_numbers = user.sign_items.get("杯面", 0)
        # 还可以使用的道具次数
        left_numbers = max_num_limit - cup_numbers
        # 使用次数大于剩余次数
        if left_numbers <= 0:
            await BagUser.add_property(user_id, group_id, goods_name, num=num)
            return f"咱今天收不下你的杯面了！要不你还是留到下次吧(＞ロ＜)"
        if num > left_numbers:
            true_use_numbers = left_numbers
            await BagUser.add_property(user_id, group_id, goods_name, num=num-left_numbers)
            reply = f"咱就只拿{true_use_numbers}个杯面就好了噢，多余的{num-left_numbers}个杯面咱收不下啦̋(๑˃́ꇴ˂̀๑)"
        else:
            true_use_numbers = num
            reply = f"要给咱{true_use_numbers}个杯面吗？那咱就心存感激地收下啦(*ˊᗜˋ*)/"
        for i in range(true_use_numbers):
            if cup_numbers == 0:
                await SignGroupUser.add_property(user_id, group_id, goods_name)
                await user.update(extra_impression=user.extra_impression + 0.05).apply()
            elif cup_numbers == 1:
                await SignGroupUser.add_property(user_id, group_id, goods_name)
                await user.update(extra_impression=user.extra_impression + 0.06).apply()
            elif cup_numbers == 2:
                await SignGroupUser.add_property(user_id, group_id, goods_name)
                await user.update(
                    extra_impression=user.extra_impression + 0.07,
                    impression_promoted_time=datetime.now() + timedelta(hours=24)
                ).apply()
            cup_numbers += 1
        return reply

    @shop_register(
        name="补签卡",
        price=500,
        des="为什么长得像餐卡的东西会有补签的作用(?)",
        effect="补回过去漏签的天数，日期从小奏入群的那天起，但不享受任何道具加成",
        load_status=True,
        daily_limit=0,
        is_passive=False,
        is_show=True,
        icon="resigncard.png",
        **{"max_num_limit": 999}
    )
    async def replenish_sign(user_id: int, group_id: int, goods_name: str, num: int):
        # 提示用户直接使用专用指令使用此道具
        await BagUser.add_property(user_id, group_id, goods_name, num=num)
        return '请直接发送 "补签" 使用此道具吧'


# 商品注册器(包括加入数据库、注册三种使用函数)
class ShopRegister(dict):
    def __init__(self, *args, **kwargs):
        super(ShopRegister, self).__init__(*args, **kwargs)
        self._data = {}
        self._flag = True

    def before_handle(self, name: Union[str, Tuple[str, ...]], load_status: bool = True):
        """
        说明:
            使用前检查方法
        参数:
            :param name: 道具名称
            :param load_status: 加载状态
        """
        def register_before_handle(name_list: Tuple[str, ...], func: Callable):
            if load_status:
                for name_ in name_list:
                    if not self._data[name_]:
                        self._data[name_] = {}
                    if not self._data[name_].get('before_handle'):
                        self._data[name_]['before_handle'] = []
                    self._data[name]['before_handle'].append(func)
        _name = (name,) if isinstance(name, str) else name
        return lambda func: register_before_handle(_name, func)

    def after_handle(self, name: Union[str, Tuple[str, ...]], load_status: bool = True):
        """
        说明:
            使用后执行方法
        参数:
            :param name: 道具名称
            :param load_status: 加载状态
        """
        def register_after_handle(name_list: Tuple[str, ...], func: Callable):
            if load_status:
                for name_ in name_list:
                    if not self._data[name_]:
                        self._data[name_] = {}
                    if not self._data[name_].get('after_handle'):
                        self._data[name_]['after_handle'] = []
                    self._data[name_]['after_handle'].append(func)
        _name = (name,) if isinstance(name, str) else name
        return lambda func: register_after_handle(_name, func)

    def register(
        self,
        name: Tuple[str, ...],
        price: Tuple[float, ...],
        des: Tuple[str, ...],
        effect: Tuple[str, ...],
        discount: Tuple[float, ...],
        limit_time: Tuple[int, ...],
        load_status: Tuple[bool, ...],
        daily_limit: Tuple[int, ...],
        is_passive: Tuple[bool, ...],
        is_show: Tuple[bool, ...],
        icon: Tuple[str, ...],
        **kwargs,
    ):
        def add_register_item(func: Callable):
            if name in self._data.keys():
                raise ValueError("该商品已注册，请替换其他名称！")
            for n, p, d, e, dd, l, s, dl, pa, sh, i in zip(
                name, price, des, effect, discount, limit_time,
                load_status, daily_limit, is_passive, is_show, icon
            ):
                if s:
                    _temp_kwargs = {}
                    for key, value in kwargs.items():
                        if key.startswith(f"{n}_"):
                            _temp_kwargs[key.split("_", maxsplit=1)[-1]] = value
                        else:
                            _temp_kwargs[key] = value
                    temp = self._data.get(n, {})
                    temp.update({
                        "price": p,
                        "des": d,
                        "effect":e,
                        "discount": dd,
                        "limit_time": l,
                        "daily_limit": dl,
                        "icon": i,
                        "is_passive": pa,
                        "is_show": sh,
                        "func": func,
                        "kwargs": _temp_kwargs,
                    })
                    self._data[n] = temp
            return func

        return lambda func: add_register_item(func)

    async def load_register(self):
        require('use')
        require('shop_handle')
        from .use.data_source import register_use, func_manager
        from .shop_handle.data_source import register_goods
        # 统一进行注册
        if self._flag:
            # 只进行一次注册
            self._flag = False
            for name in self._data.keys():
                # 注册商品信息
                await register_goods(
                    name,
                    self._data[name]["price"],
                    self._data[name]["des"],
                    self._data[name]["effect"],
                    self._data[name]["discount"],
                    self._data[name]["limit_time"],
                    self._data[name]["daily_limit"],
                    self._data[name]["is_passive"],
                    self._data[name]["is_show"],
                    self._data[name]["icon"],
                )
                # 注册商品使用函数
                register_use(name, self._data[name]["func"], **self._data[name]["kwargs"])
                # 注册商品使用前后函数
                func_manager.register_use_before_handle(name, self._data[name].get('before_handle', []))
                func_manager.register_use_after_handle(name, self._data[name].get('after_handle', []))

    def __call__(
        self,
        name: Union[str, Tuple[str, ...]],                  # 名称
        price: Union[float, Tuple[float, ...]],             # 价格
        des: Union[str, Tuple[str, ...]],                   # 简介
        effect: Union[str, Tuple[str, ...]],                # 效果
        discount: Union[float, Tuple[float, ...]] = 1,      # 折扣
        limit_time: Union[int, Tuple[int, ...]] = 0,        # 限时
        load_status: Union[bool, Tuple[bool, ...]] = True,  # 加载状态
        daily_limit: Union[int, Tuple[int, ...]] = 0,       # 每日限购
        is_passive: Union[bool, Tuple[bool, ...]] = False,  # 被动道具（无法被'使用道具'命令消耗）
        is_show: Union[bool, Tuple[bool, ...]] = True,     # 道具是否展示在商店内
        icon: Union[str, Tuple[str, ...]] = False,          # 图标
        **kwargs,
    ):
        _tuple_list = []
        _current_len = -1
        for x in [name, price, des, effect, discount, limit_time, load_status]:
            if isinstance(x, tuple):
                if _current_len == -1:
                    _current_len = len(x)
                if _current_len != len(x):
                    raise ValueError(f"注册商品 {name} 中 name，price，des，effect，discount，limit_time，load_status 数量不符！")
        _current_len = _current_len if _current_len > -1 else 1
        _name = self.__get(name, _current_len)
        _price = self.__get(price, _current_len)
        _discount = self.__get(discount, _current_len)
        _limit_time = self.__get(limit_time, _current_len)
        _des = self.__get(des, _current_len)
        _effect = self.__get(effect, _current_len)
        _load_status = self.__get(load_status, _current_len)
        _daily_limit = self.__get(daily_limit, _current_len)
        _is_passive = self.__get(is_passive, _current_len)
        _is_show = self.__get(is_show, _current_len)
        _icon = self.__get(icon, _current_len)
        return self.register(
            _name,_price,_des,_effect,_discount,_limit_time,_load_status,
            _daily_limit,_is_passive,_is_show,_icon,**kwargs,
        )

    def __get(self, value, _current_len):
        return value if isinstance(value, tuple) else tuple([value for _ in range(_current_len)])

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __str__(self):
        return str(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


shop_register = ShopRegister()
