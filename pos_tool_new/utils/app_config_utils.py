import sys
import os

def get_app_config_path():
    """获取 app.config 的绝对路径，兼容打包环境"""
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "app.config")


def get_app_config_value(key, default=None):
    """读取 app.config 指定 key 的值，未找到则返回 default"""
    config_path = get_app_config_path()
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() == key:
                        return v.strip()
    return default


def set_app_config_value(key, value):
    """设置 app.config 指定 key 的值，保留其它配置"""
    config_path = get_app_config_path()
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    config[k.strip()] = v.strip()
    config[key] = str(value)
    with open(config_path, "w", encoding="utf-8") as f:
        for k, v in config.items():
            f.write(f"{k}={v}\n")
