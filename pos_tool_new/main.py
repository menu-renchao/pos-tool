import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Tuple

from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QMovie
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTabWidget, QTextEdit,
    QPushButton, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QGroupBox, QProgressBar,
    QMainWindow, QToolBar, QToolButton
)

from pos_tool_new.backend import Backend
from pos_tool_new.version_info.version_info import VersionInfoDialog


def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，支持PyInstaller打包后的路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class BaseTabWidget(QWidget):
    """基础选项卡组件，提供通用功能"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(2)  # 减少间距
        self.layout.setContentsMargins(3, 3, 3, 3)  # 减少边距

    def create_warning_label(self, message: str) -> QLabel:
        """创建警告标签"""
        warn = QLabel(message)
        warn.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-weight: bold;
                font-size: 12px;  # 缩小字体
                background-color: #ffebee;
                padding: 6px;  # 减少内边距
                border-radius: 3px;
                border: 1px solid #ffcdd2;
            }
        """)
        warn.setWordWrap(True)
        return warn

    def create_env_selector(self, default: str = "QA") -> Tuple[QWidget, QButtonGroup]:
        """创建环境选择器"""
        group = QButtonGroup()
        frame = QWidget()
        layout = QHBoxLayout(frame)
        layout.setSpacing(1)  # 减少间距
        layout.setContentsMargins(2, 2, 2, 2)  # 减少边距

        for name in ["PROD", "QA", "DEV"]:
            btn = QRadioButton(name)
            btn.setStyleSheet("QRadioButton { font-size: 11px; }")  # 缩小字体
            group.addButton(btn)
            layout.addWidget(btn)
            if name == default:
                btn.setChecked(True)

        layout.addStretch()
        return frame, group

    def get_selected_env(self, button_group: QButtonGroup) -> str:
        """获取选中的环境"""
        for btn in button_group.buttons():
            if btn.isChecked():
                return btn.text()
        return "QA"

    def add_help_button(self, parent_button: QPushButton, info: str):
        """为按钮添加帮助按钮"""
        help_btn = QToolButton()
        help_btn.setIcon(QIcon(resource_path("UI/help.png")))
        help_btn.setToolTip("点击查看使用说明")
        help_btn.clicked.connect(lambda: self.show_upgrade_help(info))
        help_btn.setStyleSheet("QToolButton { background: transparent; border: none; }")
        help_btn.setFixedSize(12, 12)  # 缩小按钮尺寸

        # 将帮助按钮添加到父按钮的布局中
        parent_button_layout = QHBoxLayout(parent_button)
        parent_button_layout.setContentsMargins(0, 0, 0, 0)
        parent_button_layout.addStretch()
        parent_button_layout.addWidget(help_btn)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_backend()
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowIcon(QIcon(resource_path('UI/app.ico')))
        self.setWindowTitle("POS测试工具 v1.5.0.1 by Mansuper")
        self.resize(900, 580)  # 缩小默认窗口尺寸

        # 设置样式
        self.setup_styles()

        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(3, 3, 3, 3)  # 减少边距
        main_layout.setSpacing(2)  # 减少间距

        # 创建顶部工具栏
        self.create_toolbar(main_layout)

        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs)

        # 创建选项卡内容

        from pos_tool_new.linux_pos.linux_window import LinuxTabWidget
        self.linux_tab = LinuxTabWidget(self)

        from pos_tool_new.windows_pos.windows_window import WindowsTabWidget
        self.windows_tab = WindowsTabWidget(self)

        from pos_tool_new.caller_id.caller_window import CallerIdTabWidget
        self.caller_tab = CallerIdTabWidget(self.backend, self)

        from pos_tool_new.license_backup.license_window import LicenseToolTabWidget
        self.license_tab = LicenseToolTabWidget(self)

        from pos_tool_new.download_war.download_war_window import DownloadWarTabWidget
        self.download_war_tab = DownloadWarTabWidget(self)

        from pos_tool_new.generate_img.generate_img_window import GenerateImgTabWidget
        self.generate_img_tab = GenerateImgTabWidget(self)


        self.tabs.addTab(self.linux_tab, "Linux POS")
        self.tabs.addTab(self.windows_tab, "Windows POS")
        self.tabs.addTab(self.caller_tab, "Caller ID")
        self.tabs.addTab(self.license_tab, "License Backup")
        self.tabs.addTab(self.download_war_tab, "Download War")
        self.tabs.addTab(self.generate_img_tab, "图片生成")
        # 创建日志区域
        self.create_log_area(main_layout)

        # 初始化进度条动画
        self.fake_progress = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_fake_progress)

    def create_toolbar(self, layout: QVBoxLayout):
        """创建顶部工具栏"""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(2)  # 减少间距
        toolbar_layout.addStretch()

        # 版本信息按钮
        self.version_btn = QPushButton("版本信息")
        self.version_btn.clicked.connect(self.show_version_info)
        self.version_btn.setMaximumWidth(80)  # 缩小按钮宽度
        self.version_btn.setStyleSheet("QPushButton { font-size: 11px; padding: 4px 8px; }")  # 缩小字体和内边距

        # 创建工具栏并添加按钮
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))  # 缩小工具栏图标尺寸
        toolbar.addWidget(self.version_btn)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        layout.addLayout(toolbar_layout)

    def show_version_info(self):
        """显示版本信息对话框"""
        dialog = VersionInfoDialog(self)
        dialog.exec()

    def setup_backend(self):
        """设置后端"""
        self.backend = Backend()
        self.backend.log_signal.connect(self.append_log)

    def setup_styles(self):
        """设置应用程序样式"""
        app.setStyle("Fusion")

        # 创建现代调色板
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(76, 163, 224))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)

        # 设置更小的字体
        app.setFont(QFont("Segoe UI", 9))  # 缩小字体大小

        # 设置紧凑的样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;  /* 缩小字体 */
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 0.5ex;  /* 减少上边距 */
                padding-top: 6px;  /* 减少内边距 */
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px 0 3px;  /* 减少内边距 */
            }
            QPushButton {
                background-color: #4ca3e0;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;  /* 减少内边距 */
                font-weight: 500;
                font-size: 11px;  /* 缩小字体 */
            }
            QPushButton:hover {
                background-color: #3a92ce;
            }
            QPushButton:pressed {
                background-color: #2a7bb8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QPushButton.clear-log {
                background-color: #e1e1e1;
                color: #333333;
            }
            QPushButton.clear-log:hover {
                background-color: #d0d0d0;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 5px 10px;  /* 减少内边距 */
                margin-right: 1px;  /* 减少右边距 */
                font-size: 11px;  /* 缩小字体 */
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;  /* 减少上边距 */
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;  /* 减少内边距 */
                background: white;
                selection-background-color: #4ca3e0;
                font-size: 11px;  /* 缩小字体 */
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #4ca3e0;
            }
            QLabel {
                color: #333333;
                font-size: 11px;  /* 缩小字体 */
            }
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;  /* 缩小字体 */
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;  /* 减少内边距 */
                background: white;
                selection-background-color: #4ca3e0;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                background: white;
                height: 16px;  /* 缩小高度 */
                color: #DC143C;
                font-size: 10px;  /* 缩小字体 */
            }
            QProgressBar::chunk {
                background-color: #4ca3e0;
                border-radius: 3px;
            }
            QToolBar {
                spacing: 2px;  /* 减少工具栏间距 */
                padding: 1px;  /* 减少内边距 */
            }
        """)

    def create_log_area(self, layout: QVBoxLayout):
        """创建日志区域"""
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(2)  # 减少间距
        log_layout.setContentsMargins(3, 3, 3, 3)  # 减少边距

        # 日志工具栏
        log_toolbar = QHBoxLayout()
        log_toolbar.setSpacing(2)  # 减少间距
        log_toolbar.addStretch()
        self.log_text = QTextEdit()
        # 清除日志按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.setMaximumWidth(80)  # 缩小按钮宽度
        clear_btn.clicked.connect(self.log_text.clear)
        clear_btn.setObjectName("clear-log")
        log_toolbar.addWidget(clear_btn)

        log_layout.addLayout(log_toolbar)

        # 日志文本区域

        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)  # 缩小最小高度
        log_layout.addWidget(self.log_text)

        # 添加自定义状态栏（居中显示）
        status_layout = QHBoxLayout()
        status_layout.setSpacing(2)  # 减少间距
        status_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(400)  # 缩小进度条宽度
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        # 新增速率显示标签
        self.speed_label = QLabel()
        self.speed_label.setVisible(False)
        self.speed_label.setMinimumWidth(100)  # 缩小标签宽度
        self.speed_label.setStyleSheet("QLabel { font-size: 10px; }")  # 缩小字体
        status_layout.addWidget(self.speed_label)

        status_layout.addStretch()
        log_layout.addLayout(status_layout)

        layout.addWidget(log_group)

    def show_upload_speed(self, speed_text):
        self.speed_label.setText(speed_text)
        self.speed_label.setVisible(True)

    def hide_upload_speed(self):
        self.speed_label.setVisible(False)
        self.speed_label.clear()

    def append_log(self, msg: str):
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg_with_time = f"[{timestamp}] {msg}"
        self.log_text.append(msg_with_time)
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def setup_progress_animation(self, interval: int):
        """设置进度条动画"""
        self.fake_progress = 0
        self.progress_timer.start(interval)

    def update_fake_progress(self):
        """更新模拟进度"""
        if self.fake_progress < 99:
            self.fake_progress += 1
            self.progress_bar.setValue(self.fake_progress)
        else:
            self.progress_timer.stop()

    def on_restart_finished(self):
        """重启完成处理"""
        self.progress_timer.stop()
        self.progress_bar.setVisible(True)

        # 获取当前进度
        current_value = self.progress_bar.value()
        target_value = 100
        step = (target_value - current_value) / 100  # 每次增加的步长

        # 创建定时器
        self.finish_timer = QTimer(self)
        self.finish_timer.setInterval(20)  # 每 20 毫秒更新一次

        def update_progress():
            nonlocal current_value
            if current_value < target_value:
                current_value += step
                self.progress_bar.setValue(int(current_value))
            else:
                self.finish_timer.stop()
                self.progress_bar.setValue(target_value)
                self.progress_bar.setVisible(False)

        self.finish_timer.timeout.connect(update_progress)
        self.finish_timer.start()


class SplashScreen(QWidget):
    def __init__(self, gif_path, duration=2000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(900, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie = QMovie(gif_path)
        self.label.setMovie(self.movie)
        layout.addWidget(self.label)

        self.duration = duration
        self.main_window = None

    def start(self, main_window_creator):
        """启动动画并创建主窗口"""
        self.movie.start()
        self.show()

        # 立即开始创建主窗口
        self.main_window = main_window_creator()

        # 定时关闭启动画面
        QTimer.singleShot(self.duration, self.close)

    def closeEvent(self, event):
        """关闭时显示主窗口"""
        self.movie.stop()
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = SplashScreen(resource_path('UI/loading.gif'), duration=2000)
    splash.movie.start()
    splash.show()

    def show_main():
        main_window = MainWindow()
        main_window.show()
        splash.close()

    QTimer.singleShot(2000, show_main)
    sys.exit(app.exec())