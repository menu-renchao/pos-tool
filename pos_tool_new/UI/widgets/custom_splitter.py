from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSplitter, QSplitterHandle


class CustomSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        # 画三个点
        color = QColor('#555' if self._hover else '#888')
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        dot_d = 4  # 直径
        spacing = 6
        total_w = dot_d * 3 + spacing * 2
        start_x = (w - total_w) // 2
        cy = h // 2
        for i in range(3):
            cx = start_x + i * (dot_d + spacing) + dot_d // 2
            painter.drawEllipse(cx, cy - dot_d // 2, dot_d, dot_d)


class CustomSplitter(QSplitter):
    def createHandle(self):
        return CustomSplitterHandle(self.orientation(), self)
