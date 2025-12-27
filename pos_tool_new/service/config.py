# 服务器配置
CONFIG = {
    # WebSocket聊天服务器配置
    "websocket": {
        "host": "0.0.0.0",
        "port": 56789
    },

    # HTTP服务器配置
    "http": {
        "host": "0.0.0.0",
        "port": 5001
    },

    # 版本管理配置
    "version_management": {
        "build_dir": "E:\\service",
        "exe_prefix": "PosTestUtil_v",
        "exe_suffix": ".exe",
        "version_info_path": "E:\\service\\version_info.html"
    },

    # Playwright配置
    "playwright": {
        "browser_dir": "~/AppData/Local/ms-playwright",
        "timeout": 1000
    }
}