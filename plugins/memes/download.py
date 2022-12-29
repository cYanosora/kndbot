from utils.imageutils import BuildImage
from configs.path_config import RESOURCE_PATH

data_path = RESOURCE_PATH / "image" / "memes"


def load_image(path: str) -> BuildImage:
    return BuildImage.open(data_path / "images" / path)


def load_thumb(path: str) -> BuildImage:
    return BuildImage.open(data_path / "thumbs" / path)
