import nonebot
from nonebot import Driver
from nonebot.plugin import require
from datetime import datetime, timedelta
from typing import Callable, Tuple, Union
from manager import Config
from models.bag_user import BagUser
from models.sign_group_user import SignGroupUser

driver: Driver = nonebot.get_driver()


@driver.on_startup
async def init_default_shop_goods():
    """
    导入内置的六个商品
    """

    @shop_register(
        name=("好感度双倍加持卡Ⅰ", "好感度双倍加持卡Ⅱ", "好感度双倍加持卡Ⅲ", "好感度双倍加持卡MAX"),
        price=(100, 180, 250, 700),
        des=(
            "下次签到双倍好感度概率 + 10%（同类商品将覆盖）",
            "下次签到双倍好感度概率 + 20%（同类商品将覆盖）",
            "下次签到双倍好感度概率 + 30%（同类商品将覆盖）",
            "下次签到必定双倍好感度（同类商品将覆盖）"
        ),
        load_status=Config.get_config("shop", "IMPORT_DEFAULT_SHOP_GOODS"),
        ** {"好感度双倍加持卡Ⅰ_prob": 0.1, "好感度双倍加持卡Ⅰ_itemname": "好感度双倍加持卡Ⅰ",
            "好感度双倍加持卡Ⅱ_prob": 0.2, "好感度双倍加持卡Ⅱ_itemname": "好感度双倍加持卡Ⅱ",
            "好感度双倍加持卡Ⅲ_prob": 0.3, "好感度双倍加持卡Ⅲ_itemname": "好感度双倍加持卡Ⅲ",
            "好感度双倍加持卡MAX_prob": 1, "好感度双倍加持卡MAX_itemname": "好感度双倍加持卡MAX"},
    )
    async def sign_card(user_id: int, group_id: int, prob: float, itemname: str):
        user = await SignGroupUser.ensure(user_id, group_id, True)
        old_sign_items = [i for i in user.sign_items.keys() if i.startswith("好感度双倍加持卡")]
        if old_sign_items:
            old_sign_items = old_sign_items[0]
            new_sign_items = user.sign_items
            new_sign_items[itemname] = new_sign_items.pop(old_sign_items)
            await user.update(add_probability=prob, sign_items=new_sign_items).apply()
            await BagUser.add_property(user_id, group_id, old_sign_items)
            if itemname == old_sign_items:
                reply = f"你已经使用过同名道具了噢？"
            else:
                reply = f"你使用 {itemname} 覆盖了当前道具 {old_sign_items} 的加成效果！原道具归还给你咯..."
            return reply
        else:
            await user.update(add_probability=prob).apply()
            await SignGroupUser.add_property(user_id, group_id, itemname)

    @shop_register(
        name="杯面",
        price=100,
        des="下次签到时提高好感增长基值,使用3次临时提高好感等级",
        load_status=True,
        **{"itemname": "杯面", "max_num_limit": 3}
    )
    async def cup_noodle(user_id: int, group_id: int, itemname: str, max_num_limit: int, num: int):
        user = await SignGroupUser.ensure(user_id, group_id)
        # 已使用的道具次数
        cup_numbers = user.sign_items.get("杯面", 0)
        # 还可以使用的道具次数
        left_numbers = max_num_limit - cup_numbers
        # 使用次数大于剩余次数
        if left_numbers <= 0:
            await BagUser.add_property(user_id, group_id, itemname, num=num)
            return f"咱今天收不下你的杯面了！要不你还是留到下次吧(＞ロ＜)"
        if num > left_numbers:
            true_use_numbers = left_numbers
            await BagUser.add_property(user_id, group_id, itemname, num=num-left_numbers)
            reply = f"咱就只拿{true_use_numbers}个杯面就好了噢，多余的{num-left_numbers}个杯面咱收不下啦̋(๑˃́ꇴ˂̀๑)"
        else:
            true_use_numbers = num
            reply = f"要给咱{true_use_numbers}个杯面吗？那咱就心存感激地收下啦(*ˊᗜˋ*)/"
        for i in range(true_use_numbers):
            if cup_numbers == 0:
                await SignGroupUser.add_property(user_id, group_id, itemname)
                await user.update(extra_impression=user.extra_impression + 0.05).apply()
            elif cup_numbers == 1:
                await SignGroupUser.add_property(user_id, group_id, itemname)
                await user.update(extra_impression=user.extra_impression + 0.06).apply()
            elif cup_numbers == 2:
                await SignGroupUser.add_property(user_id, group_id, itemname)
                await user.update(
                    extra_impression=user.extra_impression + 0.07,
                    impression_promoted_time=datetime.now() + timedelta(hours=24)
                ).apply()
            cup_numbers += 1
        return reply

    @shop_register(
            name="补签卡",
            price=500,
            des="补回过去漏签的天数，日期从小奏入此群的那天算起",
            load_status=True,
            **{"itemname": "补签卡", "max_num_limit": 999}
        )
    async def replenish_sign(user_id: int, group_id: int, itemname: str, num: int):
        # 提示用户直接使用专用指令使用此道具
        await BagUser.add_property(user_id, group_id, itemname, num=num)
        return '请直接发送 "补签" 使用此道具吧'


@driver.on_bot_connect
async def _():
    await shop_register.load_register()


class ShopRegister(dict):
    def __init__(self, *args, **kwargs):
        super(ShopRegister, self).__init__(*args, **kwargs)
        self._data = {}
        self._flag = True

    def register(
        self,
        name: Tuple[str, ...],
        price: Tuple[float, ...],
        des: Tuple[str, ...],
        discount: Tuple[float, ...],
        limit_time: Tuple[int, ...],
        load_status: Tuple[bool, ...],
        **kwargs,
    ):
        def add_register_item(func: Callable):
            if name in self._data.keys():
                raise ValueError("该商品已注册，请替换其他名称！")
            for n, p, d, dd, l, s in zip(name, price, des, discount, limit_time, load_status):
                if s:
                    _temp_kwargs = {}
                    for key, value in kwargs.items():
                        if key.startswith(f"{n}_"):
                            _temp_kwargs[key.split("_", maxsplit=1)[-1]] = value
                        else:
                            _temp_kwargs[key] = value
                    self._data[n] = {
                        "price": p,
                        "des": d,
                        "discount": dd,
                        "limit_time": l,
                        "func": func,
                        "kwargs": _temp_kwargs,
                    }
            return func

        return lambda func: add_register_item(func)

    async def load_register(self):
        require('use')
        require('shop_handle')
        from .use.data_source import register_use
        from .shop_handle.data_source import register_goods
        # 统一进行注册
        if self._flag:
            # 只进行一次注册
            self._flag = False
            for name in self._data.keys():
                await register_goods(
                    name, self._data[name]["price"], self._data[name]["des"], self._data[name]["discount"], self._data[name]["limit_time"]
                )
                register_use(
                    name, self._data[name]["func"], **self._data[name]["kwargs"]
                )

    def __call__(
        self,
        name: Union[str, Tuple[str, ...]],
        price: Union[float, Tuple[float, ...]],
        des: Union[str, Tuple[str, ...]],
        discount: Union[float, Tuple[float, ...]] = 1,
        limit_time: Union[int, Tuple[int, ...]] = 0,
        load_status: Union[bool, Tuple[bool, ...]] = True,
        **kwargs,
    ):
        _tuple_list = []
        _current_len = -1
        for x in [name, price, des, discount, limit_time, load_status]:
            if isinstance(x, tuple):
                if _current_len == -1:
                    _current_len = len(x)
                if _current_len != len(x):
                    raise ValueError(f"注册商品 {name} 中 name，price，des，discount，limit_time，load_status 数量不符！")
        _current_len = _current_len if _current_len > -1 else 1
        _name = name if isinstance(name, tuple) else (name,)
        _price = (
            price
            if isinstance(price, tuple)
            else tuple([price for _ in range(_current_len)])
        )
        _discount = (
            discount
            if isinstance(discount, tuple)
            else tuple([discount for _ in range(_current_len)])
        )
        _limit_time = (
            limit_time
            if isinstance(limit_time, tuple)
            else tuple([limit_time for _ in range(_current_len)])
        )
        _des = (
            des if isinstance(des, tuple) else tuple([des for _ in range(_current_len)])
        )
        _load_status = (
            load_status
            if isinstance(load_status, tuple)
            else tuple([load_status for _ in range(_current_len)])
        )
        return self.register(_name, _price, _des, _discount, _limit_time, _load_status, **kwargs)

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
