import os
import sys


def get_app_config_path():
    """获取 app.config 的绝对路径"""
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "app.config")


def read_config():
    """读取 app.config 内容为字典"""
    config = {}
    path = get_app_config_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    config[k.strip()] = v.strip()
    return config


def write_config(config):
    """将字典内容写入 app.config"""
    path = get_app_config_path()
    with open(path, "w", encoding="utf-8") as f:
        for k, v in config.items():
            f.write(f"{k}={v}\n")


TAB_ID_MAP = {
    "linux_pos": "🐧 Linux POS",
    "linux_file_config": "⚙️ Linux配置文件",
    "win_pos": "🪟 Windows POS",
    "win_file_config": "⚙️ Windows配置文件",
    "db_config": "🗄️ 数据库配置",
    "scan_pos": "🔍 扫描POS",
    "scan_printer": "🖨️ 扫描打印机/刷卡机",
    "caller_id": "📞 Caller ID",
    "license": "🔐 Device&&App License",
    "download_war": "📥 Download War",
    "generate_img": "🖼️ 图片生成",
    "random_mail": "📧 随机邮箱",
    "sms": "📱 短信验证码",
    "lan_chat": "💬 消息广播"
}
TAB_ID_LIST = list(TAB_ID_MAP.keys())


def load_tab_config_from_app():
    """加载tab显示状态和顺序"""
    config = read_config()
    tabs = {tid: config.get(tid, 'true').lower() == 'true' for tid in TAB_ID_LIST}
    tab_order = config.get('tab_order', ','.join(TAB_ID_LIST)).split(',')
    tab_order = [tid for tid in tab_order if tid in TAB_ID_LIST]
    for tid in TAB_ID_LIST:
        if tid not in tab_order:
            tab_order.append(tid)
    return {"tabs": tabs, "tab_order": tab_order}


def save_tab_config_to_app(tabs, tab_order):
    """保存tab显示状态和顺序到 app.config"""
    config = read_config()
    config.update({tid: str(tabs.get(tid, True)) for tid in TAB_ID_LIST})
    config['tab_order'] = ','.join(tab_order)
    write_config(config)


def get_app_config_value(key, default=None):
    config = read_config()
    return config.get(key, default)


def set_app_config_value(key, value):
    config = read_config()
    config[key] = str(value)
    write_config(config)


def get_remark(merchant_id):
    """获取指定merchant_id的备注"""
    key = f"remark_{merchant_id}"
    return get_app_config_value(key, "")


def set_remark(merchant_id, remark):
    """设置指定merchant_id的备注，Free Trials不写入配置文件"""
    if merchant_id == "Free Trials":
        return
    key = f"remark_{merchant_id}"
    set_app_config_value(key, remark)


def get_tc_session_ids():
    """获取TCSESSIONID配置，返回dict"""
    config = read_config()
    return {
        "TCSESSIONID_1": config.get("TCSESSIONID_1", "2507ED4FAACCF3B89F28EFB2AF5E8F1F"),
        "TCSESSIONID_2": config.get("TCSESSIONID_2", "765BD3E3AD0BF5B9185394176B0AAEC5")
    }


def set_tc_session_ids(tc1, tc2):
    """设置TCSESSIONID配置"""
    config = read_config()
    config["TCSESSIONID_1"] = tc1
    config["TCSESSIONID_2"] = tc2
    write_config(config)
