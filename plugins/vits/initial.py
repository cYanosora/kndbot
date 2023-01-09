import os
from pathlib import Path
from typing import List, Dict
from nonebot.log import logger


async def checkDir(*args):
    for path in args:
        if not os.path.exists(path):
            logger.info(f"{path}目录不存在，正在创建...")
            try:
                os.mkdir(path)
                logger.info(f"{path}目录创建成功")
            except:
                logger.info(f"{path}目录创建失败")


async def checkFile(
        model_path: Path,
        config_path: Path,
        filenames: List,
        tts_gal: Dict,
        valid_names: List
):
    """
    检查各模型文件是否存在
    """
    exist_file = []
    for filename in filenames:
        flag = True
        model_file = filename + ".pth"
        config_file = filename + ".json"
        if not os.path.exists(model_path / model_file):
            logger.info(f"模型文件{model_file}缺失")
            flag = False
        if not os.path.exists(config_path / config_file):
            logger.info(f"配置文件{config_file}缺失")
            flag = False
        if flag:
            exist_file.append(filename)
    
    # 添加目前检测出来的可以使用的角色语音
    valid_names += [name for name,model in tts_gal.items() if model[0] in exist_file]




