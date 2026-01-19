"""
主窗口进度管理模块
"""
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget

from pos_tool_new.UI.styles import get_speed_label_style, get_bottom_widget_style
from pos_tool_new.UI.widgets import AnimatedProgressBar


class ProgressManager:
    """进度管理器"""

    def __init__(self, window):
        self.window = window
        self.progress_timer: Optional[QTimer] = None
        self.fake_progress: int = 0
        self.progress_bar: Optional[AnimatedProgressBar] = None
        self.speed_label: Optional[QLabel] = None
        self.finish_timer: Optional[QTimer] = None

    def setup_progress_components(self):
        """设置进度相关组件"""
        self.progress_timer = QTimer(self.window)
        self.progress_bar = AnimatedProgressBar(self.window)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("处理中... %p%")

        self.speed_label = QLabel()
        self.speed_label.setVisible(False)
        self.speed_label.setMinimumWidth(120)
        self.speed_label.setStyleSheet(get_speed_label_style())

    def create_bottom_widget(self) -> QWidget:
        """创建底部部件"""
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        bottom_layout.setSpacing(16)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.speed_label)
        bottom_layout.addStretch()

        bottom_widget.setStyleSheet(get_bottom_widget_style())

        return bottom_widget

    def setup_progress_timer(self):
        """设置进度条定时器"""
        self.fake_progress = 0
        self.progress_timer.timeout.connect(self.update_fake_progress)

    def update_fake_progress(self):
        """更新模拟进度"""
        if self.fake_progress < 99:
            self.fake_progress += 1
            self.progress_bar.setValue(self.fake_progress)
        else:
            self.progress_timer.stop()

    def setup_progress_animation(self, interval: int):
        """设置进度条动画"""
        self.fake_progress = 0
        self.progress_timer.start(interval)

    def on_restart_finished(self):
        """重启完成处理"""
        # 确保 finish_timer 已初始化且为 QTimer 实例
        if not hasattr(self, 'finish_timer') or self.finish_timer is None:
            self.finish_timer = QTimer(self.window)
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

    def show_upload_speed(self, speed_text):
        """显示上传速度"""
        self.speed_label.setText(f"📊 {speed_text}")
        self.speed_label.setVisible(True)

    def hide_upload_speed(self):
        """隐藏上传速度"""
        self.speed_label.setVisible(False)
