from nonebot import Config, get_driver
from configs.path_config import RESOURCE_PATH, RECORD_PATH

base_path = RESOURCE_PATH / "tts"
voice_path = RECORD_PATH / "temp"
model_path = base_path / "model"
config_path = base_path / "config"
plugin_config = Config.parse_obj(get_driver().config)
