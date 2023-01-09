from pathlib import Path
from torch import load
try:
  import ujson as json
except:
  import json


class HParams():
  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      if type(v) == dict:
        v = HParams(**v)
      self[k] = v

  def keys(self):
    return self.__dict__.keys()

  def items(self):
    return self.__dict__.items()

  def values(self):
    return self.__dict__.values()

  def __len__(self):
    return len(self.__dict__)

  def __getitem__(self, key):
    return getattr(self, key)

  def __setitem__(self, key, value):
    return setattr(self, key, value)

  def __contains__(self, key):
    return key in self.__dict__

  def __repr__(self):
    return self.__dict__.__repr__()


def load_checkpoint(checkpoint_path: Path, model):
    """
    将配置文件导入模型
    """
    checkpoint_dict = load(checkpoint_path, map_location='cpu')
    iteration = checkpoint_dict['iteration']
    saved_state_dict = checkpoint_dict['model']
    if hasattr(model, 'module'):
        state_dict = model.module.state_dict()
    else:
        state_dict = model.state_dict()
    new_state_dict= {}
    for k, v in state_dict.items():
        try:
          new_state_dict[k] = saved_state_dict[k]
        except:
          new_state_dict[k] = v
    if hasattr(model, 'module'):
        model.module.load_state_dict(new_state_dict)
    else:
        model.load_state_dict(new_state_dict)
    return


def get_hparams_from_file(config_path: Path) -> HParams:
  with open(config_path, "r") as f:
    data = f.read()
  config = json.loads(data)
  hparams = HParams(**config)
  return hparams
