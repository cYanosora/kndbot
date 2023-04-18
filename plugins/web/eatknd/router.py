import json
import math
import time
import requests
from jose import jwt
from pathlib import Path
from fastapi import APIRouter, Response, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.http_utils import AsyncHttpx
from .auth import decrypt, encrypt
from .models import PlayResult, Query, Token, SumbitResult
from .schema import EatkndRecord, EatkndToken
from .exception import HTTPException, request_error

route = APIRouter(prefix='/game/eatknd')
templates_directory = Path(__file__).parent / "templates"
static_directory = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_directory))


@route.get('/static/{file_path:path}')
async def static_file(file_path: str):
    return FileResponse(static_directory / file_path)


@route.get('/rank')
async def rank(
    request: Request,
    type: str = 'all',
    page: int = 1,
    query: str = '',
):
    if type not in ['all', 'day', 'week', 'month', 'query']:
        raise request_error
    elif type == 'query' and not query:
        raise request_error
    lang = request.headers.get('Accept-Language')[:2] or 'zh'
    lang_file = static_directory / f'i18n/{lang}.json'
    with open(lang_file, 'r', encoding='utf-8') as f:
        i18n = json.load(f)
    try:
        token = request.cookies.get('token')
        payload = decrypt(token)
        user_id = payload['user_id']
    except:
        user_id = None
    user = await EatkndRecord.get(int(user_id), type) if user_id else None
    max_pages = 9
    num = 10
    offset = (page - 1) * num
    if type != 'query':
        rows = await EatkndRecord.get_len(type)
        rows = min(num * max_pages, rows)
        total = math.ceil(rows / num)
        total_ranks = await EatkndRecord.get_list(type, num, offset, True)
    else:
        total_ranks = await EatkndRecord.query_user('all', query, is_fuzzy=True)
        total = len(total_ranks)
    return templates.TemplateResponse("rank.html", {
        "request": request,
        "data": total_ranks,  # 排行榜玩家数据
        "i18n": i18n,  # i18n文案设置
        "user": user,  # 玩家数据(optional)
        "RankingType": type,  # 排行类型
        "CurrentPage": page,  # 当前页数
        "total": total,  # 总记录数
    })


@route.post('/submit', response_model=SumbitResult)
async def submit(request: Request, result: PlayResult):
    unauth_resp = {"message": "未检测到有效用户，无法上传分数"}
    success_resp = {"message": "分数已上传成功"}
    too_long_resp = {"message": "无法上传分数，请缩短用户名、留言~"}
    too_fast_resp = {"message": "无法上传分数，5秒内只能上传一次哦~"}
    # 检查token
    token = request.cookies.get('token')
    if not token:
        return unauth_resp
    try:
        payload = decrypt(token)
        user_id = payload['user_id']
    except jwt.JWTError:
        return unauth_resp
    time_limit = 5
    current_t = time.time()
    if current_t - result.last_time // 1000 <= time_limit:
        return too_fast_resp
    if 0 <= len(result.nickname) <= 30 and 0 <= len(result.message) <= 150:
        # 获取ip位置信息
        api_url = rf'http://ip.taobao.com/outGetIpInfo?ip="{request.client.host}&accessKey=alibaba-inc'
        try:
            data = (await AsyncHttpx.get(api_url)).json()
        except:
            data = requests.get(api_url).json()
        try:
            area = data['data']['country']
        except:
            area = 'Unknown'
        # 获取设备信息
        user_agent = request.headers.get('user-agent').lower()
        try:
            system_dict = {
                'windows nt': 'Windows', 'macintosh': 'Mac', 'ipod': 'iPod', 'ipad': 'iPad',
                'iphone': 'iPhone', 'android': 'Android', 'unix': 'Unix', 'linux': 'Linux'
            }
            key = next(filter(lambda x: x in user_agent, list(system_dict.keys())))
            system = system_dict[key]
        except:
            system = 'Other'
        # 玩家记录
        for type in ['all', 'month', 'week', 'day']:
            await EatkndRecord.set(
                user_id, type,
                result.score, result.nickname,
                result.message, system, area
            )
        return success_resp
    return too_long_resp


@route.get('/{target}')
async def eatkanade(target: str, response: Response):
    user = await EatkndToken.get_user_by_token(target)
    if not user:
        return RedirectResponse(url='/game/eatknd')
    encoded_jwt = encrypt({"user_id": user.user_id})
    response.set_cookie('token', encoded_jwt, httponly=True)
    headers = {"Set-Cookie": response.headers.get("set-cookie")}
    return RedirectResponse(url='/game/eatknd', headers=headers)


@route.get('/')
async def eatkanade():
    file_path = templates_directory / 'index.html'
    return FileResponse(file_path)


@route.post('/token', response_model=Token)
async def token(body: Query):
    target = body.id
    if not target:
        raise HTTPException(422, detail="请求体需要包含id")
    user = await EatkndToken.get_user_by_token(target)
    if not user:
        raise HTTPException(422, detail="不存在于此id相对应的用户")
    encoded_jwt = encrypt({"user_id": user.user_id})
    return {"token": encoded_jwt}
