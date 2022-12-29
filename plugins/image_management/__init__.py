from manager import Config
from configs.path_config import IMAGE_PATH
import nonebot


Config.add_plugin_config(
    "image_management",
    "IMAGE_DIR_LIST",
    ["美图", "壁纸", "表情包"],
    name="图库操作",
    help_="公开图库列表，可自定义添加",
    default_value=[],
)

Config.add_plugin_config(
    "image_management",
    "WITHDRAW_IMAGE_MESSAGE",
    (0, 1),
    name="图库操作",
    help_="自动撤回，参1：延迟撤回发送图库图片的时间(秒)，0 为关闭 | 参2：监控聊天类型，0(私聊) 1(群聊) 2(群聊+私聊)",
    default_value=(0, 1),
)

Config.add_plugin_config(
    "image_management:delete_image",
    "DELETE_IMAGE_LEVEL [LEVEL]",
    7,
    help_="删除图库图片需要的管理员等级",
    default_value=7,
)

Config.add_plugin_config(
    "image_management:move_image",
    "MOVE_IMAGE_LEVEL [LEVEL]",
    7,
    help_="移动图库图片需要的管理员等级",
    default_value=7,
)

Config.add_plugin_config(
     "image_management:upload_image",
     "UPLOAD_IMAGE_LEVEL",
     6,
     help_="上传图库图片需要的管理员等级",
     default_value=6,
)

Config.add_plugin_config(
    "image_management",
    "SHOW_ID",
    False,
    help_="是否消息显示图片下标id",
    default_value=False
)

Config.add_plugin_config(
    "pjsk_alias",
    "BANWORDS",
    ["老婆_老婆", "老公_老公", "肯尼迪_1"],
    help_="禁止出现的角色称呼，用_分隔称呼与类型，1代表仅不允许设置的称呼，否则代表不允许设置且有特殊回复",
    default_value=["老婆_老婆", "老公_老公", "肯尼迪_1"]
)

(IMAGE_PATH / "image_management").mkdir(parents=True, exist_ok=True)


nonebot.load_plugins("plugins/image_management")
