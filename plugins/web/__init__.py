from fastapi.middleware.cors import CORSMiddleware
import nonebot
from .eatknd import route as eatknd_route
from .pjsk_api import route as pic_route
__plugin_name__ = '网页相关'


app = nonebot.get_app()
app.include_router(pic_route)
app.include_router(eatknd_route)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nonebot.load_plugins('plugins/web')