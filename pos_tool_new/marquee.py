from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy


class MarqueeBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(22)
        self.marquee_bar = QLabel("")
        self.marquee_bar.setMinimumHeight(22)
        self.marquee_bar.setStyleSheet("""
            QLabel {
                background: #fffbe6;
                color: #d48806;
                font-weight: normal;
                font-size: 12px;
                border-bottom: 1px solid #ffe58f;
                padding-left: 10px;
            }
        """)
        # 关键：防止内容撑大主窗口，必须用 Ignored
        self.marquee_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.marquee_bar.setMinimumWidth(0)
        self.marquee_bar.setMaximumWidth(16777215)
        self.marquee_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.marquee_bar.setWordWrap(False)

        self.marquee_text = ""
        self.scroll_position = 0
        self.display_text = ""  # 实际显示的文本（不含填充）
        self.is_scrolling = False  # 标记是否正在滚动

        self.marquee_timer = QTimer(self)
        self.marquee_timer.timeout.connect(self._scroll_marquee)

        self.marquee_close_btn = QPushButton()
        self.marquee_close_btn.setText("×")
        self.marquee_close_btn.setFixedSize(28, 22)
        self.marquee_close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #d48806;
                font-size: 20px;
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
        self.is_scrolling = False

    def _get_display_len(self):
        """优化显示长度计算"""
        font_metrics = self.marquee_bar.fontMetrics()
        bar_width = self.marquee_bar.width()

        if bar_width <= 0:
            return 1

        # 使用更准确的平均字符宽度计算
        sample_text = "中文English123混合"  # 混合字符样本
        avg_char_width = font_metrics.horizontalAdvance(sample_text) / len(sample_text)

        if avg_char_width <= 0:
            return 1

        # 考虑内边距和关闭按钮宽度
        available_width = bar_width # 10px padding-left + 28px 关闭按钮
        display_len = max(1, int(available_width / avg_char_width))

        return display_len-35

    def _scroll_marquee(self):
        """优化滚动逻辑，支持平滑滚动"""
        if not self.marquee_text or not self.is_scrolling:
            return

        display_len = self._get_display_len()

        # 如果文本长度小于显示长度，不需要滚动
        if len(self.display_text) <= display_len:
            self.marquee_bar.setText(self.display_text)
            self.marquee_timer.stop()
            self.is_scrolling = False
            return

        # 计算滚动位置
        start_pos = self.scroll_position
        end_pos = start_pos + display_len

        # 获取显示文本
        if end_pos <= len(self.marquee_text):
            show_text = self.marquee_text[start_pos:end_pos]
        else:
            # 循环滚动：文本末尾 + 文本开头
            remaining = end_pos - len(self.marquee_text)
            show_text = self.marquee_text[start_pos:] + self.marquee_text[:remaining]

        # 更新显示
        self.marquee_bar.setText(show_text)

        # 更新滚动位置
        self.scroll_position += 1
        if self.scroll_position >= len(self.marquee_text):
            self.scroll_position = 0


        self.marquee_timer.setInterval(200)

    def update_marquee_message(self, msg: str):
        """优化消息更新逻辑"""
        if not msg:
            self.setVisible(False)
            self.marquee_timer.stop()
            self.marquee_closed_by_user = False
            self.is_scrolling = False
            return

        # 清理消息
        msg = msg.replace('\r', ' ').replace('\n', ' ').strip()
        if not msg:
            return

        self.display_text = msg  # 保存原始显示文本

        # 计算显示长度
        display_len = self._get_display_len()

        # 判断是否需要滚动
        needs_scrolling = len(msg) > display_len
        if needs_scrolling:
            # 需要滚动：构建循环文本
            # 在原始文本后添加空格和重复文本，形成平滑循环
            separator = " " * 5  # 5个空格作为分隔
            loop_text = msg + separator + msg

            # 确保循环文本足够长（至少3倍显示长度）
            min_length = 3 * display_len
            while len(loop_text) < min_length:
                loop_text += separator + msg

            self.marquee_text = loop_text
            self.scroll_position = 0
            self.is_scrolling = True

            # 初始显示文本末尾部分，让滚动更自然
            initial_text = msg[-display_len:] if len(msg) > display_len else msg
            self.marquee_bar.setText(initial_text)

            self.marquee_timer.start(200)
        else:
            # 不需要滚动：直接显示完整文本
            self.marquee_text = msg
            self.marquee_bar.setText(msg)
            self.marquee_timer.stop()
            self.is_scrolling = False

        # 显示跑马灯
        self.setVisible(True)
        self.marquee_closed_by_user = False

    def resizeEvent(self, event):
        """窗口大小变化时重新计算显示"""
        super().resizeEvent(event)

        if self.isVisible():  # 去掉 and self.is_scrolling，保证每次resize都能正确判断
            # 重新计算显示长度并重置滚动
            display_len = self._get_display_len()
            needs_scrolling = len(self.display_text) > display_len
            if needs_scrolling and not self.marquee_timer.isActive():
                # 需要滚动但定时器未启动，重新启动
                self.update_marquee_message(self.display_text)
            elif not needs_scrolling and self.marquee_timer.isActive():
                # 不需要滚动但定时器在运行，停止滚动
                self.marquee_bar.setText(self.display_text)
                self.marquee_timer.stop()
                self.is_scrolling = False

