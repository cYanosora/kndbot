from configs.path_config import RESOURCE_PATH

NOT_BIND_ERROR = "出错了，可能是因为没有绑定"
ID_ERROR = "你这ID有问题啊"
TIMEOUT_ERROR = "出错了，可能是bot网不好"
BUG_ERROR = "出错了，可能是バグ捏"
REFUSED_ERROR = "查不到捏，可能是不给看"
NOT_PLAYER_ERROR = "未找到玩家"
NOT_IMAGE_ERROR = "部分资源加载失败，重新发送中..."
MAINTAIN_ERROR = "出错了，可能是游戏正在维护"
USER_BAN_ERROR = "出错了，可能是用户已被封禁"
NOT_SERVER_ERROR = "出错了，不支持此服务器"
QUERY_BAN_ERROR = "该用户已被拉黑，禁止使用此功能"
ONLY_TOP100_ERROR = "出错了，目前查分仅支持前百的玩家"

# api
base_url = r'https://api.unipjsk.com/api'
base_url_bak1 = r'https://api.pjsekai.moe/api'
api_base_url_list = [base_url]

# 榜线url
all_levels_url = r'https://api.sekai.best/event/live?region=jp'

# 活动号url
current_event_url = r'https://api.pjsek.ai/database/user/userHomeBanners'
current_event_url_bak = r'https://strapi.sekai.best/sekai-current-event'

# 推车url
ycm_url = 'http://59.110.175.37:5000/'

# 预测线url
pred_url = r'https://33.dsml.hk/pred'
pred_url_bak = r'https://api.sekai.best/event/pred?region=jp'

# 5v5人数url
cheer_pred_url = r'https://33.dsml.hk/cheer-pred'
cheer_pred_url_bak = base_url + r'/cheerful-carnival-team-count'

# 日服游戏json资源url
json_url = r'https://gitlab.com/pjsekai/database/jp/-/raw/main'
json_url_bak = r'https://raw.fastgit.org/Sekai-World/sekai-master-db-diff/main'

# 日服游戏数仓资源url
db_url = r'https://assets.unipjsk.com'
db_url_bak = r'https://assets.pjsek.ai/file/pjsekai-assets'

# 活动号
event_id = 75

# 榜线排名号
rank_levels = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    20, 30, 40, 50, 100,
    200, 300, 400, 500, 1000,
    2000, 3000, 4000, 5000, 10000,
    20000, 30000, 40000, 50000, 100000
]

# 排位称号
rankmatchgrades = {
    1: 'ビギナー(初学者)',
    2: 'ブロンズ(青铜)',
    3: 'シルバー(白银)',
    4: 'ゴールド(黄金)',
    5: 'プラチナ(白金)',
    6: 'ダイヤモンド(钻石)',
    7: 'マスター(大师)'
}

# 通用headers
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ja;q=0.5',
    'cache-control': 'max-age=0',
    'sec-ch-ua': '"Microsoft Edge";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.42'
}

lab_headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ja;q=0.5',
    'cache-control': 'max-age=0',
    'if-none-match': 'W/"8c1c9d56a00342d904ddfe7609c54d72"',
    'sec-ch-ua': '"Microsoft Edge";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.42'
}
# 预测线数据
pred_score_json = {"data": {}, "time": 0, "id": event_id}

# 烧烤资源存放路径
data_path = RESOURCE_PATH / "masterdata"
if not data_path.exists():
    data_path.mkdir(parents=True, exist_ok=True)

# 烧烤用户suite存放路径
suite_path = data_path / "user_suites"
if not suite_path.exists():
    suite_path.mkdir(parents=True, exist_ok=True)