import nonebot
from fastapi.middleware.cors import CORSMiddleware


__plugin_name__ = '网页相关'
nonebot.load_plugins('plugins/web')
from .eatknd import route as eatknd_route


app = nonebot.get_app()
app.include_router(eatknd_route)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

