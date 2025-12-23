from pos_tool_new.base_tab import BaseTabWidget
from .lan_chat_service import LanChatService
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from datetime import datetime


class LanChatTab(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__('消息广播', parent)
        self.service = LanChatService(self.on_message_received)
        self.unread_count = 0
        self.parent_tab_widget = parent.tabs if hasattr(parent, 'tabs') else None
        self.tab_index = None
        self.init_ui()
        self.service.start_listen()

    def init_ui(self):
        layout = self.layout
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 昵称设置区域
        nick_layout = QHBoxLayout()
        nick_layout.setSpacing(10)

        nick_label = QLabel('昵称:')
        nick_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        nick_layout.addWidget(nick_label)

        self.nickname_edit = QLineEdit('匿名')
        self.nickname_edit.setFont(QFont("Microsoft YaHei", 10))
        self.nickname_edit.setPlaceholderText("请输入您的昵称")
        self.nickname_edit.setMinimumHeight(30)
        self.nickname_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px 10px;
                background-color: #f9f9f9;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
                background-color: white;
            }
        """)
        nick_layout.addWidget(self.nickname_edit)

        self.set_nick_btn = QPushButton('设置昵称')
        self.set_nick_btn.setFont(QFont("Microsoft YaHei", 10))
        self.set_nick_btn.setMinimumHeight(30)
        self.set_nick_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.set_nick_btn.clicked.connect(self.set_nickname)
        nick_layout.addWidget(self.set_nick_btn)

        layout.addLayout(nick_layout)

        # 消息显示区域
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Microsoft YaHei", 10))
        self.text_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                background-color: #f5f5f5;
                min-height: 300px;
            }
        """)
        layout.addWidget(self.text_display)

        # 消息输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Microsoft YaHei", 10))
        self.input_edit.setPlaceholderText("输入消息...")
        self.input_edit.setMinimumHeight(35)
        self.input_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        input_layout.addWidget(self.input_edit)

        self.send_btn = QPushButton('发送')
        self.send_btn.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.send_btn.setMinimumHeight(35)
        self.send_btn.setMinimumWidth(80)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # 设置输入框回车发送消息
        self.input_edit.returnPressed.connect(self.send_btn.click)

    def set_nickname(self):
        nickname = self.nickname_edit.text().strip()
        if nickname:
            self.service.set_nickname(nickname)
            # 添加设置成功的视觉反馈
            self.nickname_edit.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    padding: 5px 10px;
                    background-color: #f0fff0;
                }
            """)

    def send_message(self):
        msg = self.input_edit.text().strip()
        if msg:
            self.service.send_message(msg)
            self.input_edit.clear()

    def on_message_received(self, nickname, message):
        now = datetime.now().strftime('%H:%M:%S')
        self.text_display.append(f'<b>{nickname}</b> [{now}] : {message}')
        self.text_display.verticalScrollBar().setValue(
            self.text_display.verticalScrollBar().maximum()
        )
        # 新消息提醒逻辑
        if not self.isVisible():
            self.increase_unread_count()

    def increase_unread_count(self):
        self.unread_count += 1
        self.update_tab_text()

    def reset_unread_count(self):
        if self.unread_count > 0:
            self.unread_count = 0
            self.update_tab_text()

    def update_tab_text(self):
        if self.parent_tab_widget is not None:
            if self.tab_index is None:
                # 查找本tab的index
                for i in range(self.parent_tab_widget.count()):
                    if self.parent_tab_widget.widget(i) is self:
                        self.tab_index = i
                        break
            if self.tab_index is not None:
                base_text = "💬 消息广播"
                if self.unread_count > 0:
                    base_text += f' ({self.unread_count})'
                self.parent_tab_widget.setTabText(self.tab_index, base_text)

    def closeEvent(self, event):
        self.service.stop()
        super().closeEvent(event)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()
        self.reset_unread_count()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()