import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtCore import QTimer, Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QMovie
from PyQt6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout
)


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
        self.version_label = self._create_label("v1.5.1.3 - 正在加载...", "12px", "#aaaaaa")

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
