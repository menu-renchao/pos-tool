from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QProgressBar


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
