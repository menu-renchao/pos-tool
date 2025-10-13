import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pos_tool_new.utils.log_manager import global_log_manager
from typing import Tuple
from PyQt6.QtCore import QTimer, Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QMovie, QTextCharFormat, QTextCursor
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
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(3, 3, 3, 3)

    @staticmethod
    def create_warning_label(message: str) -> QLabel:
        """创建警告标签"""
        warn = QLabel(message)
        warn.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-weight: bold;
                font-size: 12px;
                background-color: #ffebee;
                padding: 6px;
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
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)
        for name in ["PROD", "QA", "DEV"]:
            btn = QRadioButton(name)
            btn.setStyleSheet("QRadioButton { font-size: 11px; }")
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


class EnhancedTextEdit(QTextEdit):
    """增强的文本编辑框，支持彩色日志"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def append_colored_text(self, text: str, color: str = "#000000"):
        """添加带颜色的文本"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        format = QTextCharFormat()
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        cursor.insertText(text + "\n")
        # 自动滚动到底部
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        )


class AnimatedProgressBar(QProgressBar):
    """带动画效果的进度条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def start_animation(self, duration=1000):
        """开始动画"""
        self.animation.setDuration(duration)
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.start()

    def stop_animation(self):
        """停止动画"""
        self.animation.stop()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fake_progress = 0
        self.progress_timer = QTimer(self)
        self.setup_backend()
        self.setup_ui()
        global_log_manager.log_received.connect(self.log_text.append_colored_text)

    def setup_ui(self):
        """设置UI"""
        self.setWindowIcon(QIcon(resource_path('UI/app.ico')))
        self.setWindowTitle("POS测试工具 v1.5.0.1 by Mansuper")
        self.resize(900, 580)
        # 设置样式
        self.setup_styles()
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.setSpacing(2)
        # 创建顶部工具栏
        self.create_toolbar(main_layout)
        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(False)
        main_layout.addWidget(self.tabs)
        # 创建选项卡内容
        self.create_tab_contents()
        # 创建日志区域
        self.create_log_area(main_layout)
        # 初始化进度条
        self.fake_progress = 0
        self.progress_timer.timeout.connect(self.update_fake_progress)

    def create_tab_contents(self):
        from pos_tool_new.linux_pos.linux_window import LinuxTabWidget
        self.linux_tab = LinuxTabWidget(self)
        self.tabs.addTab(self.linux_tab, "🐧 Linux POS")
        from pos_tool_new.windows_pos.windows_window import WindowsTabWidget
        self.windows_tab = WindowsTabWidget(self)
        self.tabs.addTab(self.windows_tab, "🪟 Windows POS")
        from pos_tool_new.caller_id.caller_window import CallerIdTabWidget
        self.caller_tab = CallerIdTabWidget(self.backend, self)
        self.tabs.addTab(self.caller_tab, "📞 Caller ID")
        from pos_tool_new.license_backup.license_window import LicenseToolTabWidget
        self.license_tab = LicenseToolTabWidget(self)
        self.tabs.addTab(self.license_tab, "🔐 License Backup")
        from pos_tool_new.download_war.download_war_window import DownloadWarTabWidget
        self.download_war_tab = DownloadWarTabWidget(self)
        self.tabs.addTab(self.download_war_tab, "📥 Download War")
        from pos_tool_new.generate_img.generate_img_window import GenerateImgTabWidget
        self.generate_img_tab = GenerateImgTabWidget(self)
        self.tabs.addTab(self.generate_img_tab, "🖼️ 图片生成")
        # 连接选项卡切换信号
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """选项卡切换事件"""
        tab_names = ["Linux POS", "Windows POS", "Caller ID", "License Backup", "Download War", "图片生成"]
        if 0 <= index < len(tab_names):
            self.append_log(f"📁 切换到选项卡: {tab_names[index]}", "info")

    def create_toolbar(self, layout: QVBoxLayout):
        """创建顶部工具栏 - 修复布局问题"""
        # 直接创建工具栏，不通过布局嵌套
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        # 版本信息按钮
        self.version_btn = QPushButton("📋 版本信息")
        self.version_btn.clicked.connect(self.show_version_info)
        self.version_btn.setMaximumWidth(100)
        self.version_btn.setStyleSheet("""
            QPushButton { 
                font-size: 11px; 
                padding: 6px 10px;
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        # 添加按钮到工具栏
        toolbar.addWidget(self.version_btn)
        toolbar.addSeparator()
        # 添加工具栏到主窗口
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def show_version_info(self):
        """显示版本信息对话框"""
        dialog = VersionInfoDialog(self)
        dialog.exec()

    def setup_backend(self):
        """设置后端"""
        self.backend = Backend()
        self.backend.log_signal.connect(lambda msg: self.append_log(msg, "info"))

    def setup_styles(self):
        """设置应用程序样式"""
        app.setStyle("Fusion")
        # 创建现代调色板
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(33, 37, 41))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(248, 249, 250))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(33, 37, 41))
        palette.setColor(QPalette.ColorRole.Text, QColor(33, 37, 41))
        palette.setColor(QPalette.ColorRole.Button, QColor(248, 249, 250))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(33, 37, 41))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(220, 53, 69))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 123, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
        # 设置字体
        app.setFont(QFont("Microsoft YaHei", 9))
        # 设置现代化的样式表
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
            }
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-top: 0.5ex;
                padding-top: 8px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #495057;
            }
       QPushButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #7fbfff, stop: 1 #4a90e2);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 500;
    font-size: 11px;
}
QPushButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #6bacff, stop: 1 #3a7bc8);
}
QPushButton:pressed {
    background: #2c6aa8;
}
QPushButton:disabled {
    background: #a0a0a0;
    color: #d0d0d0;
}
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 11px;
                color: #495057;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                color: #007bff;
                font-weight: 600;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
                background: #e9ecef;
            }
            QTabBar::tab:hover:!selected {
                background: #dee2e6;
            }
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px;
                background: white;
                selection-background-color: #007bff;
            }
            /* 进度条样式优化 */
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 4px;
                text-align: center;
                background: #f8f9fa;
                height: 20px;
                color: #495057;
                font-size: 10px;
                font-weight: 500;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00b09b, stop: 1 #96c93d);
                border-radius: 3px;
                margin: 0.5px;
            }
            QToolBar {
                background: #f8f9fa;
                border: none;
                border-bottom: 1px solid #dee2e6;
                spacing: 4px;
                padding: 4px;
            }
            QToolBar::separator {
                background: #dee2e6;
                width: 1px;
                margin: 0 4px;
            }
        """)

    def create_log_area(self, layout: QVBoxLayout):
        """创建日志区域"""
        log_group = QGroupBox("📝 操作日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(4)
        log_layout.setContentsMargins(6, 6, 6, 6)
        # 日志工具栏
        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()
        # 清除日志按钮
        clear_btn = QPushButton("🗑️ 清除日志")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self.clear_logs)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        log_toolbar.addWidget(clear_btn)
        log_layout.addLayout(log_toolbar)
        # 日志文本区域
        self.log_text = EnhancedTextEdit()
        self.log_text.setMinimumHeight(120)
        log_layout.addWidget(self.log_text)
        # 状态栏区域
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        # 进度条
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("处理中... %p%")
        status_layout.addWidget(self.progress_bar)
        # 速率显示标签
        self.speed_label = QLabel()
        self.speed_label.setVisible(False)
        self.speed_label.setMinimumWidth(120)
        self.speed_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #28a745;
                font-weight: 500;
                background: #d4edda;
                padding: 2px 6px;
                border-radius: 3px;
                border: 1px solid #c3e6cb;
            }
        """)
        status_layout.addWidget(self.speed_label)
        status_layout.addStretch()
        log_layout.addLayout(status_layout)
        layout.addWidget(log_group)

    def filter_logs(self, button):
        """过滤日志显示"""
        # 这里可以实现按级别过滤日志的功能
        level = button.text()
        self.append_log(f"已过滤显示: {level}级别日志", "info")

    def clear_logs(self):
        """清除日志"""
        self.log_text.clear()

    def show_upload_speed(self, speed_text):
        """显示上传速度"""
        self.speed_label.setText(f"📊 {speed_text}")
        self.speed_label.setVisible(True)

    def hide_upload_speed(self):
        """隐藏上传速度"""
        self.speed_label.setVisible(False)

    def setup_progress_animation(self, interval: int):
        self.fake_progress = 0
        self.progress_timer.start(interval)

    def update_fake_progress(self):
        if self.fake_progress < 99:
            self.fake_progress += 1
            self.progress_bar.setValue(self.fake_progress)
        else:
            self.progress_timer.stop()

    def on_restart_finished(self):
        """重启完成处理"""
        self.progress_timer.stop()
        self.progress_bar.setVisible(True)
        current_value = self.progress_bar.value()
        target_value = 100
        step = max((target_value - current_value) / 30, 1)  # 30帧内完成，最小步长1

        # 初始化 finish_timer（只需一次）
        if not hasattr(self, 'finish_timer'):
            from PyQt6.QtCore import QTimer
            self.finish_timer = QTimer(self)
        self.finish_timer.stop()
        try:
            self.finish_timer.timeout.disconnect()
        except Exception:
            pass

        def update_progress():
            nonlocal current_value
            if current_value < target_value:
                current_value += step
                if current_value > target_value:
                    current_value = target_value
                self.progress_bar.setValue(int(current_value))
            else:
                self.finish_timer.stop()
                self.progress_bar.setValue(target_value)
                self.progress_bar.setVisible(False)

        self.finish_timer.timeout.connect(update_progress)
        self.finish_timer.start(20)

    def append_log(self, msg, level="info"):
        global_log_manager.log(msg, level)


class ModernSplashScreen(QWidget):
    """现代化的启动画面"""

    def __init__(self, gif_path, duration=1800, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 300)
        # 设置半透明背景
        self.setStyleSheet("""
            ModernSplashScreen {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2);
                border-radius: 15px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 应用图标
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_pixmap = QIcon(resource_path('UI/app.ico')).pixmap(64, 64)
        self.icon_label.setPixmap(icon_pixmap)
        layout.addWidget(self.icon_label)
        # 加载动画
        self.animation_label = QLabel()
        self.animation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie = QMovie(gif_path)
        if self.movie.isValid():
            self.movie.setScaledSize(QSize(80, 80))
            self.animation_label.setMovie(self.movie)
        else:
            # 如果GIF加载失败，显示静态文本
            self.animation_label.setText("加载中...")
            self.animation_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.animation_label)
        # 应用标题
        self.title_label = QLabel("POS测试工具")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
        """)
        layout.addWidget(self.title_label)
        # 版本信息
        self.version_label = QLabel("v1.5.0.1 - 正在加载...")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                background: transparent;
            }
        """)
        layout.addWidget(self.version_label)
        # 进度条
        self.splash_progress = QProgressBar()
        self.splash_progress.setMaximumWidth(300)
        self.splash_progress.setTextVisible(False)
        self.splash_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.2);
                height: 6px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ffecd2, stop: 1 #fcb69f);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.splash_progress)
        self.duration = duration
        self.main_window = None
        # 启动进度动画
        self.progress_animation = QPropertyAnimation(self.splash_progress, b"value")
        self.progress_animation.setDuration(duration)
        self.progress_animation.setStartValue(0)
        self.progress_animation.setEndValue(100)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def start(self, main_window_creator):
        """启动动画并创建主窗口"""
        if self.movie.isValid():
            self.movie.start()
        self.progress_animation.start()
        self.show()
        # 创建主窗口（在后台）
        self.main_window = main_window_creator()
        # 定时关闭启动画面
        QTimer.singleShot(self.duration, self.finish_loading)

    def finish_loading(self):
        """完成加载"""
        self.progress_animation.stop()
        self.splash_progress.setValue(100)
        # 确保主窗口存在且正确显示
        if self.main_window:
            # 先确保窗口属性正确设置
            self.main_window.setWindowFlags(Qt.WindowType.Window)
            self.main_window.showNormal()  # 确保正常显示模式
            self.main_window.raise_()
            self.main_window.activateWindow()
            # 添加延迟确保窗口完全显示
            QTimer.singleShot(100, lambda: self.main_window.setWindowOpacity(1))
        self.close()
        app.processEvents()  # 处理剩余事件

    def closeEvent(self, event):
        """关闭时显示主窗口"""
        if self.movie.isValid():
            self.movie.stop()
        if self.main_window:
            # 添加淡入效果
            self.main_window.setWindowOpacity(0)
            self.main_window.show()
            # 创建淡入动画
            fade_animation = QPropertyAnimation(self.main_window, b"windowOpacity")
            fade_animation.setDuration(500)
            fade_animation.setStartValue(0)
            fade_animation.setEndValue(1)
            fade_animation.start()
            self.main_window.raise_()
            self.main_window.activateWindow()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 创建现代化启动画面
    splash = ModernSplashScreen(resource_path('UI/loading.gif'), duration=1800)


    def create_main_window():
        return MainWindow()


    # 显示启动画面
    splash.start(create_main_window)
    sys.exit(app.exec())
