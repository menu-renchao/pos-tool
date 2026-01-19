from PyQt6.QtCore import QPoint, Qt, QRectF, QRect
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton


class GuideOverlay(QWidget):
    """多步骤首次运行引导蒙层"""

    def __init__(self, parent, steps):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("")
        self.steps = steps  # [(控件, 提示文本)]
        self.current_step = 0
        self.tip_label = QLabel(self)
        self.tip_label.setStyleSheet(
            "color: white; font-size: 18px; font-weight: bold; background: rgba(0,0,0,180); border-radius:8px; padding:16px;")
        self.tip_label.setWordWrap(True)  # 关闭自动换行
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setSizePolicy(self.tip_label.sizePolicy().horizontalPolicy(),
                                     self.tip_label.sizePolicy().verticalPolicy())
        self.next_btn = QPushButton(self)
        self.next_btn.setStyleSheet(
            "font-size: 16px; padding: 8px 24px; background: #007bff; color: white; border-radius: 6px;")
        self.next_btn.clicked.connect(self.next_step)
        self.update_step()
        self.setVisible(True)
        self.adjust_overlay_geometry()

    def adjust_overlay_geometry(self):
        # Ensure overlay always matches parent size and is on top
        if self.parentWidget():
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
            self.raise_()

    def showEvent(self, event):
        self.adjust_overlay_geometry()
        super().showEvent(event)

    def update_step(self):
        if self.current_step >= len(self.steps):
            self.finish_guide()
            return
        _, tip = self.steps[self.current_step]
        # 所有步骤统一为深色背景、白色字体、蓝色边框，无icon
        self.tip_label.setText(tip)
        self.tip_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            background: rgba(0,0,0,0.92);
            border: 2px solid #42a5f5;
            border-radius:12px;
            padding:18px;
            box-shadow: 0 2px 12px rgba(66,165,245,0.15);
        """)
        if self.current_step == len(self.steps) - 1:
            self.next_btn.setText("完成")
        else:
            self.next_btn.setText("下一步")
        self.repaint()
        self.update_tip_position()

    def update_tip_position(self):
        # 将tip_label和按钮放在高亮区域下方或中央
        target, _ = self.steps[self.current_step]
        if isinstance(target, QWidget) and target.isVisible():
            rect = target.rect()
            top_left = target.mapToGlobal(rect.topLeft())
            parent_top_left = self.parentWidget().mapToGlobal(QPoint(0, 0))
            rel_pos = top_left - parent_top_left
            # 放在高亮区域下方
            tip_w = min(400, self.width() - 40)
            self.tip_label.setFixedWidth(tip_w)
            self.tip_label.adjustSize()
            tip_h = self.tip_label.height()
            btn_h = 40
            x = rel_pos.x() + (rect.width() - tip_w) // 2
            y = rel_pos.y() + rect.height() + 20
            if y + tip_h + btn_h > self.height():
                y = max(20, rel_pos.y() - tip_h - btn_h - 20)
            self.tip_label.move(max(20, x), y)
            self.next_btn.move(max(20, x), y + tip_h + 10)
            self.next_btn.setFixedWidth(120)
            self.next_btn.setFixedHeight(36)
            self.tip_label.setVisible(True)
            self.next_btn.setVisible(True)
        else:
            # 非QWidget（如QAction），tip居中
            self.tip_label.setFixedWidth(min(400, self.width() - 40))
            self.tip_label.adjustSize()
            tip_h = self.tip_label.height()
            self.tip_label.move((self.width() - self.tip_label.width()) // 2, (self.height() - tip_h) // 2)
            self.next_btn.move((self.width() - 120) // 2, (self.height() + tip_h) // 2 + 10)
            self.next_btn.setFixedWidth(120)
            self.next_btn.setFixedHeight(36)
            self.tip_label.setVisible(True)
            self.next_btn.setVisible(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        target, _ = self.steps[self.current_step]
        # 只对QWidget高亮挖空
        if isinstance(target, QWidget) and target.isVisible():
            rect = target.rect()
            top_left = target.mapToGlobal(rect.topLeft())
            parent_top_left = self.parentWidget().mapToGlobal(QPoint(0, 0))
            rel_pos = top_left - parent_top_left
            highlight_rect = QRect(rel_pos, rect.size())
            path = QPainterPath()
            path.addRect(QRectF(self.rect()))
            path.addRoundedRect(QRectF(highlight_rect), 12, 12)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillPath(path, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QColor(0, 180, 255, 220))
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawRoundedRect(highlight_rect, 12, 12)

    def resizeEvent(self, event):
        self.adjust_overlay_geometry()
        self.update_tip_position()
        super().resizeEvent(event)

    def next_step(self):
        self.current_step += 1
        self.update_step()

    def finish_guide(self):
        self.setVisible(False)
        from pos_tool_new.utils.app_config_utils import set_app_config_value
        set_app_config_value('guide_shown', 'true')
