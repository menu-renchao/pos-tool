import os
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import (
    QApplication, QPushButton, QHBoxLayout,
    QLabel, QProgressBar, QMessageBox, QVBoxLayout, QDialog
)

from pos_tool_new.utils.app_config_utils import (
    get_app_config_value
)

LOCAL_VERSION = "1.5.1.5"  # 当前本地版本号，建议后续自动生成
EXE_NAME_PREFIX = "PosTestUtil_v"
EXE_SUFFIX = ".exe"
# 获取exe运行目录
EXE_RUN_DIR = os.path.dirname(sys.executable)


def get_api_url():
    """根据配置文件动态获取API_URL"""
    ip = get_app_config_value('micro_default_ip')
    port = get_app_config_value('micro_default_upgrade_port')
    return f"http://{ip}:{port}/api"


def get_local_exe_path():
    """获取本地exe路径（运行目录）"""
    for file in os.listdir(EXE_RUN_DIR):
        if file.startswith(EXE_NAME_PREFIX) and file.endswith(EXE_SUFFIX):
            return os.path.join(EXE_RUN_DIR, file)
    return None


def check_and_update_exe(parent=None):
    api_url = get_api_url()  # 每次动态获取
    try:
        r = requests.get(f"{api_url}/version", timeout=2)
        r.raise_for_status()
        latest_version = r.json().get("version")
        update_info = r.json().get("info", "")
    except Exception as e:
        dlg = UpdateDialog(parent, LOCAL_VERSION, error=str(e))
        dlg.exec()
        return
    dlg = UpdateDialog(parent, LOCAL_VERSION, latest_version, update_info)
    dlg.exec()


class UpdateDialog(QDialog):
    def __init__(self, parent, local_version, latest_version=None, update_info=None, error=None):
        super().__init__(parent)
        self.setWindowTitle("检查更新")
        self.setMinimumWidth(380)
        self.result = None
        layout = QVBoxLayout(self)
        if error:
            layout.addWidget(QLabel("<b>检查更新失败：移步【设置】->【微服务】检査ip和升级服务端口是否正确</b>"))
            btn = QPushButton("关闭")
            btn.clicked.connect(self.reject)
            layout.addWidget(btn)
            return
        layout.addWidget(QLabel(f"当前版本：<b>{local_version}</b>"))
        if latest_version is None:
            layout.addWidget(QLabel("未能获取最新版本信息。"))
            btn = QPushButton("关闭")
            btn.clicked.connect(self.reject)
            layout.addWidget(btn)
            return
        layout.addWidget(QLabel(f"最新版本：<b>{latest_version}</b>"))
        if latest_version == local_version:
            layout.addWidget(QLabel("当前已是最新版本。"))
            btn = QPushButton("关闭")
            btn.clicked.connect(self.reject)
            layout.addWidget(btn)
            return
        if update_info:
            # 兼容换行，将\n替换为<br>，并安全显示
            update_info_html = '<br>'.join(update_info.split('\n'))
            layout.addWidget(QLabel(f"<b>更新说明：</b><br>{update_info_html}"))
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        btn_update = QPushButton("立即更新")
        btn_update.clicked.connect(self.start_update)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addWidget(btn_update)
        btns.addWidget(btn_close)
        layout.addLayout(btns)
        self.latest_version = latest_version
        self.local_version = local_version
        self.parent = parent
        self.update_info = update_info
        self.setModal(True)

    def start_update(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        QApplication.processEvents()
        exe_name = f"PosTestUtil_v{self.latest_version}.exe"
        exe_path = os.path.join(EXE_RUN_DIR, exe_name)
        if os.path.exists(exe_path):
            QMessageBox.warning(self, "下载失败", f"新版本文件已存在：{exe_path}\n请先删除该文件后再重试更新。")
            self.progress.setVisible(False)
            return
        try:
            api_url = get_api_url()  # 每次动态获取
            url = f"{api_url}/download"
            r = requests.get(url, stream=True, timeout=10)
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            with open(exe_path, 'wb') as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress.setValue(int(downloaded * 100 / total))
                        QApplication.processEvents()
            self.progress.setValue(100)
            QMessageBox.information(self, "更新完成",
                                    f"新版本 {self.latest_version} 已下载。即将自动重启新版本。")
            # 写入需要清理历史文件标记和旧exe路径
            import subprocess
            old_exe = sys.executable
            from pos_tool_new.utils.app_config_utils import set_app_config_value
            set_app_config_value('need_clear_history_files', 'true')
            set_app_config_value('old_exe_path', old_exe)
            # 启动新 exe 并传递旧 exe 路径参数
            new_exe = exe_path
            try:
                subprocess.Popen([new_exe, '--cleanup', old_exe], close_fds=True)
            except Exception as e:
                QMessageBox.warning(self, "启动新版本失败", f"尝试启动新版本失败：{e}")
            self.accept()
            sys.exit(0)
        except Exception as e:
            QMessageBox.warning(self, "下载失败", f"下载新版本失败：{e}")
            self.progress.setVisible(False)
