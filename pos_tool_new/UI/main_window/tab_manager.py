"""
主窗口Tab管理模块
"""
from pos_tool_new.utils.app_config_utils import (
    load_tab_config_from_app, save_tab_config_to_app,
    TAB_ID_MAP, TAB_ID_LIST
)
from pos_tool_new.utils.log_manager import global_log_manager

TAB_IMPORTS = [
    ("linux_pos", "pos_tool_new.linux_pos.linux_window", "LinuxTabWidget"),
    ("linux_file_config", "pos_tool_new.linux_file_config.file_config_linux_window", "FileConfigTabWidget"),
    ("win_pos", "pos_tool_new.windows_pos.windows_window", "WindowsTabWidget"),
    ("win_file_config", "pos_tool_new.windows_file_config.file_config_win_window", "WindowsFileConfigTabWidget"),
    ("db_config", "pos_tool_new.db_config.db_config_window", "DbConfigWindow"),
    ("scan_pos", "pos_tool_new.scan_pos.scan_pos_window", "ScanPosTabWidget"),
    ("scan_printer", "pos_tool_new.scan_printer.scan_printer_window", "ScanPrinterTabWidget"),
    ("caller_id", "pos_tool_new.caller_id.caller_window", "CallerIdTabWidget"),
    ("license", "pos_tool_new.license_backup.license_window", "LicenseToolTabWidget"),
    ("download_war", "pos_tool_new.download_war.download_war_window", "DownloadWarTabWidget"),
    ("generate_img", "pos_tool_new.generate_img.generate_img_window", "GenerateImgTabWidget"),
    ("random_mail", "pos_tool_new.random_mail.random_mail_window", "RandomMailTabWidget"),
    ("sms", "pos_tool_new.sms.sms_window", "SmsWindow"),
    ("lan_chat", "pos_tool_new.lan_chat.lan_chat_window", "LanChatTab")
]


def load_tab_config():
    """加载Tab配置"""
    return load_tab_config_from_app()


def save_tab_config(tabs, tab_order):
    """保存Tab配置"""
    save_tab_config_to_app(tabs, tab_order)


def create_tab_contents(window):
    """创建选项卡内容"""
    config = load_tab_config()
    tab_order = config.get("tab_order", TAB_ID_LIST)
    tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})

    id_to_import = {tid: imp for tid, *imp in TAB_IMPORTS}
    ordered_imports = [(tid, *id_to_import[tid]) for tid in tab_order if tid in id_to_import]

    for tid, module_path, class_name in ordered_imports:
        if not tabs_enabled.get(tid, True):
            continue
        try:
            module = __import__(module_path, fromlist=[class_name])
            tab_class = getattr(module, class_name)
            tab_instance = tab_class(window)
            tab_text = TAB_ID_MAP.get(tid, tid)
            window.tabs.addTab(tab_instance, tab_text)
        except (ImportError, AttributeError) as e:
            global_log_manager.log(f"Failed to load tab {tid}: {e}", "error")


def refresh_tabs(window):
    """刷新选项卡"""
    while window.tabs.count():
        tab = window.tabs.widget(0)
        if hasattr(tab, 'dispose'):
            tab.dispose()
        window.tabs.removeTab(0)
    create_tab_contents(window)


def on_tab_moved(window):
    """Tab拖拽顺序变化时，保存顺序到配置"""
    tab_ids = []
    for i in range(window.tabs.count()):
        tab_text = window.tabs.tabText(i)
        for tid, cname in TAB_ID_MAP.items():
            if tab_text == cname:
                tab_ids.append(tid)
    config = load_tab_config()
    tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})
    save_tab_config(tabs_enabled, tab_ids)


def get_tab_imports():
    """获取Tab导入列表"""
    return TAB_IMPORTS
