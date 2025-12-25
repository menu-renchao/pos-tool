from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy

class MarqueeBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(28)
        self.marquee_bar = QLabel("")
        self.marquee_bar.setMinimumHeight(28)
        self.marquee_bar.setStyleSheet("""
            QLabel {
                background: #fffbe6;
                color: #d48806;
                font-weight: bold;
                font-size: 15px;
                border-bottom: 1px solid #ffe58f;
                padding-left: 16px;
            }
        """)
        self.marquee_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.marquee_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.marquee_bar.setWordWrap(False)
        self.marquee_text = ""
        self.scroll_position = 0
        self.marquee_timer = QTimer(self)
        self.marquee_timer.timeout.connect(self._scroll_marquee)
        self.marquee_close_btn = QPushButton("×")
        self.marquee_close_btn.setFixedSize(28, 28)
        self.marquee_close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #d48806;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover {
                background: #ffe58f;
            }
        """)
        self.marquee_close_btn.setToolTip("关闭跑马灯")
        self.marquee_close_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.marquee_close_btn.clicked.connect(self._close_marquee_bar)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.marquee_bar, 1)
        layout.addWidget(self.marquee_close_btn, 0)
        self.setVisible(False)
        self.marquee_closed_by_user = False

    def _close_marquee_bar(self):
        self.setVisible(False)
        self.marquee_timer.stop()
        self.marquee_closed_by_user = True

    def _get_display_len(self):
        font_metrics = self.marquee_bar.fontMetrics()
        bar_width = self.marquee_bar.width()
        char_width = font_metrics.horizontalAdvance('W')
        display_len = max(1, bar_width // char_width)
        return display_len

    def _scroll_marquee(self):
        if not self.marquee_text:
            self.marquee_bar.setText("")
            return
        display_len = self._get_display_len()
        if not hasattr(self, "scroll_position") or self.scroll_position is None:
            self.scroll_position = 0
        start_pos = self.scroll_position
        end_pos = start_pos + display_len
        if end_pos <= len(self.marquee_text):
            show_text = self.marquee_text[start_pos:end_pos]
        else:
            remaining = end_pos - len(self.marquee_text)
            show_text = self.marquee_text[start_pos:] + self.marquee_text[:remaining]
        self.marquee_bar.setText(show_text)
        self.scroll_position += 1
        if self.scroll_position >= len(self.marquee_text):
            self.scroll_position = 0

    def update_marquee_message(self, msg: str):
        if not msg:
            self.setVisible(False)
            self.marquee_timer.stop()
            self.marquee_closed_by_user = False
            return
        msg = msg.replace('\r', ' ').replace('\n', ' ')
        display_len = self._get_display_len()
        base_text = msg + (" " * display_len)
        while len(base_text) < 3 * display_len:
            base_text += msg + (" " * display_len)
        self.marquee_text = base_text
        self.scroll_position = 0
        self.setVisible(True)
        self.marquee_closed_by_user = False
        if len(msg) <= display_len:
            self.marquee_bar.setText(msg)
        else:
            self.marquee_bar.setText(msg[-display_len:])
            self.scroll_position = len(self.marquee_text) - display_len
        self.marquee_timer.start(120)

