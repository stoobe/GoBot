import pprint
from typing import Any

import tomli

cfg = None
# Read the TOML file

try:
    with open("_config.toml", "rb") as f:
        cfg = tomli.load(f)
except Exception as e:
    with open("../_config.toml", "rb") as f:
        cfg = tomli.load(f)

# # Print the parsed data
# print(f'cfg = ')
# pprint.pp(cfg)


class ConfigAccess:
    def __init__(self, cfg):
        for key, value in cfg.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        return self.__dict__[name]

    def __setattr__(self, name: str, value: Any) -> Any:
        self.__dict__[name] = value


_config = ConfigAccess(cfg)

_config.godb_url = f"mysql{_config.godb_driver}://{_config.godb_user}:{_config.godb_pw}@{_config.godb_host}:{_config.godb_port}/{_config.godb_name}"


for i in range(4):
    if i not in _config.go_rating_limits:
        _config.go_rating_limits[i] = None

# print("url ",_config.godb_url)
