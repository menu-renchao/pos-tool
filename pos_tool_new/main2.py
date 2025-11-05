import os
import sys
import time
from typing import Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtCore import QTimer, Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QTextCharFormat, QTextCursor, QAction, QIcon, QColor, QMovie
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QTextEdit, QPushButton, QHBoxLayout,
    QLabel, QRadioButton, QButtonGroup, QGroupBox, QProgressBar, QMainWindow,
    QToolButton, QMenuBar, QMessageBox, QVBoxLayout, QSplitter
)

from pos_tool_new.backend import Backend
from pos_tool_new.version_info.version_info import VersionInfoDialog
from pos_tool_new.utils.log_manager import global_log_manager


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
        help_btn.setText("?")
        help_btn.setToolTip("点击查看使用说明")
        help_btn.clicked.connect(lambda: self.show_upgrade_help(info))

        help_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid #999;
                border-radius: 8px;
                color: #555;
                font-weight: bold;
                font-size: 10px;
                padding: 0px;
            }
            QToolButton:hover {
                background: #ffeb3b;
                color: #333;
                border: 1px solid #ffc107;
            }
        """)
        help_btn.setFixedSize(20, 20)

        parent_button_layout = QHBoxLayout(parent_button)
        parent_button_layout.setContentsMargins(0, 0, 0, 0)
        parent_button_layout.addStretch()
        parent_button_layout.addWidget(help_btn)

    def show_upgrade_help(self, info: str):
        """显示升级帮助"""
        QMessageBox.information(self, "使用说明", info)

    def _find_mainwindow(self) -> Optional[QMainWindow]:
        """递归查找主窗口"""
        parent = self.parent()
        while parent is not None and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent

    def hide_main_log_area(self):
        """隐藏主窗口日志区域"""
        mainwin = self._find_mainwindow()
        if mainwin is not None:
            for gb in mainwin.findChildren(QGroupBox):
                if gb.title().strip() == "📝📝 操作日志":
                    gb.setVisible(False)
            if hasattr(mainwin, 'layout') and callable(mainwin.layout):
                mainwin.layout().activate()
            mainwin.update()

    def show_main_log_area(self):
        """显示主窗口日志区域"""
        mainwin = self._find_mainwindow()
        if mainwin is not None:
            for gb in mainwin.findChildren(QGroupBox):
                if gb.title().strip() == "📝📝 操作日志":
                    gb.setVisible(True)
            if hasattr(mainwin, 'layout') and callable(mainwin.layout):
                mainwin.layout().activate()
            mainwin.update()


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
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


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
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.finish_timer: Optional[QTimer] = None
        self.log_text: Optional[EnhancedTextEdit] = None
        self.log_group: Optional[QGroupBox] = None
        self.fake_progress: int = 0

        self._init_components()
        self.setup_backend()
        self.setup_ui()

        global_log_manager.log_received.connect(self.log_text.append_colored_text)

    def _init_components(self):
        """初始化组件"""
        self.progress_timer = QTimer(self)
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("处理中... %p%")

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

    def setup_ui(self):
        """设置UI界面"""
        self._setup_window_properties()
        self.setup_styles()
        self.create_menubar()

        central_widget = self._create_central_widget()
        self.setCentralWidget(central_widget)

        self._setup_progress_timer()

    def _setup_window_properties(self):
        """设置窗口属性"""
        self.setWindowIcon(QIcon(resource_path('UI/app.ico')))
        self.setWindowTitle("POS测试工具 v1.5.0.8 by Mansuper")
        self.resize(900, 580)

    def _create_central_widget(self) -> QWidget:
        """创建中央部件"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)

        # 创建日志区域
        self.create_log_area()

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.log_group)
        self.log_group.setMinimumHeight(270)
        splitter.setSizes([600, 180])
        main_layout.addWidget(splitter)

        # 添加底部部件
        main_layout.addWidget(self._create_bottom_widget())

        # 创建选项卡内容
        self.create_tab_contents()

        return central_widget

    def _create_bottom_widget(self) -> QWidget:
        """创建底部部件"""
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        bottom_layout.setSpacing(16)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.speed_label)
        bottom_layout.addStretch()

        bottom_widget.setStyleSheet("""
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)

        return bottom_widget

    def _setup_progress_timer(self):
        """设置进度条定时器"""
        self.fake_progress = 0
        self.progress_timer.timeout.connect(self.update_fake_progress)

    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar() or QMenuBar(self)
        about_menu = menubar.addMenu("关于(&A)")

        version_action = QAction("版本信息", self)
        version_action.triggered.connect(self.show_version_info)
        about_menu.addAction(version_action)

        self.setMenuBar(menubar)

    def create_tab_contents(self):
        """创建选项卡内容"""
        tab_imports = [
            ("pos_tool_new.linux_pos.linux_window", "LinuxTabWidget", "🐧 Linux POS"),
            ("pos_tool_new.linux_file_config.file_config_linux_window", "FileConfigTabWidget", "⚙️ Linux配置文件"),
            ("pos_tool_new.windows_pos.windows_window", "WindowsTabWidget", "🪟 Windows POS"),
            ("pos_tool_new.windows_file_config.file_config_win_window", "WindowsFileConfigTabWidget",
             "⚙️ Windows配置文件"),
            ("pos_tool_new.db_config.db_config_window", "DbConfigWindow", "🗄️ 数据库配置"),
            ("pos_tool_new.scan_pos.scan_pos_window", "ScanPosTabWidget", "🔍 扫描POS"),
            ("pos_tool_new.caller_id.caller_window", "CallerIdTabWidget", "📞 Caller ID"),
            ("pos_tool_new.license_backup.license_window", "LicenseToolTabWidget", "🔐 Device&&App License"),
            ("pos_tool_new.download_war.download_war_window", "DownloadWarTabWidget", "📥 Download War"),
            ("pos_tool_new.generate_img.generate_img_window", "GenerateImgTabWidget", "🖼️ 图片生成"),
            ("pos_tool_new.random_mail.random_mail_window", "RandomMailTabWidget", "📧 随机邮箱")
        ]

        for module_path, class_name, tab_name in tab_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                tab_class = getattr(module, class_name)

                if class_name in ["ScanPosTabWidget", "CallerIdTabWidget"]:
                    tab_instance = tab_class(self.backend, self)
                else:
                    tab_instance = tab_class(self)

                self.tabs.addTab(tab_instance, tab_name)
            except (ImportError, AttributeError) as e:
                print(f"Failed to load tab {tab_name}: {e}")

    def show_version_info(self):
        """显示版本信息"""
        dialog = VersionInfoDialog(self)
        dialog.exec()

    def setup_backend(self):
        """设置后端"""
        self.backend = Backend()
        self.backend.log_signal.connect(lambda msg: self.append_log(msg, "info"))

    def setup_styles(self):
        """设置应用程序样式"""
        app.setStyle("Fusion")

        # 创建调色板
        palette = QPalette()
        palette_configs = [
            (QPalette.ColorRole.Window, QColor(245, 245, 245)),
            (QPalette.ColorRole.WindowText, QColor(33, 37, 41)),
            (QPalette.ColorRole.Base, QColor(255, 255, 255)),
            (QPalette.ColorRole.AlternateBase, QColor(248, 249, 250)),
            (QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220)),
            (QPalette.ColorRole.ToolTipText, QColor(33, 37, 41)),
            (QPalette.ColorRole.Text, QColor(33, 37, 41)),
            (QPalette.ColorRole.Button, QColor(248, 249, 250)),
            (QPalette.ColorRole.ButtonText, QColor(33, 37, 41)),
            (QPalette.ColorRole.BrightText, QColor(220, 53, 69)),
            (QPalette.ColorRole.Highlight, QColor(0, 123, 255)),
            (QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        ]

        for role, color in palette_configs:
            palette.setColor(role, color)

        app.setPalette(palette)
        app.setFont(QFont("Microsoft YaHei", 9))

        self.setStyleSheet(self._get_stylesheet())

    def _get_stylesheet(self) -> str:
        """获取样式表"""
        return """
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
                padding: 4px; 
                min-width: 0px;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 4px 8px;
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
            QToolTip {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
                opacity: 240;
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
        """

    def create_log_area(self):
        """创建日志区域"""
        self.log_group = QGroupBox("📝 操作日志")
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setSpacing(4)
        log_layout.setContentsMargins(6, 6, 6, 6)

        # 日志工具栏
        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()

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
        if self.log_text is not None:
            self.log_text.setMinimumHeight(120)
        log_layout.addWidget(self.log_text)

    def clear_logs(self):
        """清除日志"""
        if self.log_text:
            self.log_text.clear()

    def show_upload_speed(self, speed_text):
        """显示上传速度"""
        self.speed_label.setText(f"📊 {speed_text}")
        self.speed_label.setVisible(True)

    def hide_upload_speed(self):
        """隐藏上传速度"""
        self.speed_label.setVisible(False)

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
        # 确保 finish_timer 已初始化且为 QTimer 实例
        if not hasattr(self, 'finish_timer') or self.finish_timer is None:
            self.finish_timer = QTimer(self)
        else:
            self.finish_timer.stop()
            try:
                self.finish_timer.timeout.disconnect()
            except Exception:
                pass
        self.progress_bar.setVisible(True)
        current_value = self.progress_bar.value()
        target_value = 100
        step = max((target_value - current_value) / 30, 1)

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
        """添加日志"""
        global_log_manager.log(msg, level)


class ModernSplashScreen(QWidget):
    """现代化启动画面"""

    def __init__(self, gif_path, duration=1800, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.main_window = None

        self._setup_window()
        self._setup_ui(gif_path)
        self._setup_animation()

    def _setup_window(self):
        """设置窗口属性"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(900, 580)

    def _setup_ui(self, gif_path):
        """设置UI界面"""
        self._is_dark_mode = self.palette().window().color().lightness() < 128

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 图标标签
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(self._get_icon())
        layout.addWidget(self.icon_label)

        # 动画标签
        self.animation_label = QLabel()
        self.animation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._setup_animation_gif(gif_path)
        layout.addWidget(self.animation_label)

        # 标题和版本标签
        self.title_label = self._create_label("POS测试工具", "24px", "#cccccc")
        self.version_label = self._create_label("v1.5.0.8 - 正在加载...", "12px", "#aaaaaa")

        layout.addWidget(self.title_label)
        layout.addWidget(self.version_label)

        # 进度条
        self.splash_progress = QProgressBar()
        self.splash_progress.setMaximumWidth(300)
        self.splash_progress.setTextVisible(False)
        self._setup_progress_style()
        layout.addWidget(self.splash_progress)

    def _create_label(self, text: str, font_size: str, color: str) -> QLabel:
        """创建标签"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: {font_size};
                font-weight: bold;
                background: transparent;
            }}
        """)
        return label

    def _get_icon(self):
        """获取图标"""
        icon = QIcon('UI/app.ico')
        return icon.pixmap(64, 64, QIcon.Mode.Normal if self._is_dark_mode else QIcon.Mode.Active)

    def _setup_animation_gif(self, gif_path):
        """设置动画GIF"""
        self.movie = QMovie(gif_path)
        if self.movie.isValid():
            self.movie.setScaledSize(QSize(280, 280))
            self.animation_label.setMovie(self.movie)
        else:
            self.animation_label.setText("加载中...")
            self.animation_label.setStyleSheet(
                f"color: {'white' if self._is_dark_mode else '#333333'}; font-size: 14px;")

    def _setup_progress_style(self):
        """设置进度条样式"""
        style_template = """
            QProgressBar {{
                border: 1px solid rgba({border_color});
                border-radius: 4px;
                background: rgba({bg_color});
                height: 6px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, 
                    stop: 0 {start_color}, stop: 1 {end_color});
                border-radius: 3px;
            }}
        """

        if self._is_dark_mode:
            style = style_template.format(
                border_color="255, 255, 255, 0.3",
                bg_color="255, 255, 255, 0.2",
                start_color="#ffecd2",
                end_color="#fcb69f"
            )
        else:
            style = style_template.format(
                border_color="0, 0, 0, 0.2",
                bg_color="0, 0, 0, 0.1",
                start_color="#4a6cf7",
                end_color="#2541b2"
            )

        self.splash_progress.setStyleSheet(style)

    def _setup_animation(self):
        """设置动画"""
        self.progress_animation = QPropertyAnimation(self.splash_progress, b"value")
        self.progress_animation.setDuration(self.duration)
        self.progress_animation.setStartValue(0)
        self.progress_animation.setEndValue(100)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def start(self, main_window_creator):
        """启动启动画面"""
        if self.movie.isValid():
            self.movie.start()

        self.progress_animation.start()
        self.show()

        self.main_window = main_window_creator()
        QTimer.singleShot(self.duration, self.finish_loading)

    def finish_loading(self):
        """完成加载"""
        self.progress_animation.stop()
        self.splash_progress.setValue(100)

        if self.main_window:
            self.main_window.setWindowFlags(Qt.WindowType.Window)
            self.main_window.showNormal()
            self.main_window.raise_()
            self.main_window.activateWindow()

        self.close()

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.movie.isValid():
            self.movie.stop()

        if self.main_window:
            self.main_window.show()

        event.accept()


def create_main_window():
    """创建主窗口"""
    start_time = time.time()
    win = MainWindow()
    end_time = time.time()

    cost_ms = int((end_time - start_time) * 1000)
    global_log_manager.log(f"应用启动耗时: {cost_ms} ms", "info")

    return win


if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = ModernSplashScreen(resource_path('UI/loading.gif'), duration=1800)
    splash.start(create_main_window)
    sys.exit(app.exec())

