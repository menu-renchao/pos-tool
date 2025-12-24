# lan_chat_tab.py
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QLabel, QListWidget, QSplitter)

from pos_tool_new.base_tab import BaseTabWidget


class LanChatTab(BaseTabWidget):
    # 信号定义
    connection_status_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__('💬 消息广播', parent)
        self.parent_tab_widget = parent.tabs if hasattr(parent, 'tabs') else None
        self.unread_count = 0
        self.is_connected = False

        # 初始化服务
        from .lan_chat_service import LanChatService
        self.service = LanChatService(self.on_message_received, server_url="ws://192.168.0.72:56789")
        self.service.set_callbacks(
            on_connected=self.on_connected,
            on_disconnected=self.on_disconnected,
            on_user_list=self.on_user_list_received
        )

        self.init_ui()
        self.setup_connections()
        try:
            self.service.start()
        except Exception as e:
            self.append_system_message(f"无法连接到聊天服务器: {e}")

    def init_ui(self):
        """初始化界面"""
        # 用父类的 self.layout，不要再新建 main_layout
        layout = self.layout
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # 连接状态栏
        self.status_bar = self.create_status_bar()
        layout.addLayout(self.status_bar)

        # 主内容区域
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 聊天区域
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)

        # 消息显示区域
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        self.message_display.setFont(QFont("Microsoft YaHei", 10))
        self.message_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background-color: #fafafa;
            }
        """)
        chat_layout.addWidget(self.message_display)

        # 输入区域
        input_layout = self.create_input_area()
        chat_layout.addLayout(input_layout)

        # 用户列表区域
        self.user_list_widget = QListWidget()
        self.user_list_widget.setMaximumWidth(200)
        self.user_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
        """)

        splitter.addWidget(chat_widget)
        splitter.addWidget(self.user_list_widget)
        splitter.setSizes([700, 200])

        layout.addWidget(splitter)

        # 输入状态提示
        self.typing_label = QLabel()
        self.typing_label.setStyleSheet("color: #666; font-style: italic;")
        self.typing_label.setVisible(False)
        layout.addWidget(self.typing_label)
        # 修复：初始化 typing_timer
        from PyQt6.QtCore import QTimer
        self.typing_timer = QTimer(self)
        self.typing_timer.setSingleShot(True)
        self.typing_timer.timeout.connect(self.stop_typing_indicator)

    def create_status_bar(self):
        """创建状态栏"""
        status_layout = QHBoxLayout()

        # 连接状态
        self.status_label = QLabel("连接中...")
        self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")

        # 用户数量
        self.user_count_label = QLabel("在线用户: 0")

        # 昵称设置
        nick_layout = QHBoxLayout()
        nick_label = QLabel("昵称:")
        self.nickname_edit = QLineEdit("匿名用户")
        self.nickname_edit.setMaximumWidth(150)
        self.set_nickname_btn = QPushButton("设置")

        nick_layout.addWidget(nick_label)
        nick_layout.addWidget(self.nickname_edit)
        nick_layout.addWidget(self.set_nickname_btn)

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.user_count_label)
        status_layout.addLayout(nick_layout)

        return status_layout

    def create_input_area(self):
        """创建输入区域"""
        input_layout = QHBoxLayout()

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)

        self.send_btn = QPushButton("发送")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_btn)

        return input_layout

    def setup_connections(self):
        """设置信号连接"""
        self.send_btn.clicked.connect(self.send_message)
        self.message_input.returnPressed.connect(self.send_message)
        self.set_nickname_btn.clicked.connect(self.set_nickname)

        # 输入状态检测
        self.message_input.textChanged.connect(self.on_text_changed)

    def set_nickname(self):
        """设置昵称"""
        nickname = self.nickname_edit.text().strip()
        if nickname:
            self.service.set_nickname(nickname)
            self.append_system_message(f"昵称已更改为: {nickname}")

    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if message and self.is_connected:
            self.service.send_message(message)
            self.message_input.clear()
            self.stop_typing_indicator()

    def on_text_changed(self):
        """文本变化处理输入状态"""
        if self.message_input.text().strip():
            self.service.send_typing_status(True)
            self.typing_timer.start(3000)  # 3秒后停止显示输入状态

    def stop_typing_indicator(self):
        """停止输入状态显示"""
        self.service.send_typing_status(False)
        self.typing_label.setVisible(False)

    def on_connected(self):
        """连接成功回调"""
        self.is_connected = True
        self.status_label.setText("已连接")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.send_btn.setEnabled(True)
        self.append_system_message("已连接到聊天服务器")
        self.connection_status_changed.emit(True)

    def on_disconnected(self, code, reason):
        """连接断开回调"""
        self.is_connected = False
        self.status_label.setText("连接断开")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.send_btn.setEnabled(False)
        self.append_system_message("与聊天服务器的连接已断开")
        self.connection_status_changed.emit(False)

    def on_message_received(self, nickname, message, timestamp):
        """收到消息回调"""
        # 兼容字符串和数字时间戳
        from datetime import datetime
        if isinstance(timestamp, str):
            try:
                time_obj = datetime.fromisoformat(timestamp)
            except Exception:
                time_obj = datetime.now()
        else:
            time_obj = datetime.fromtimestamp(timestamp)
        time_str = time_obj.strftime('%H:%M:%S')

        # 格式化消息显示
        if nickname == '系统':
            formatted_msg = f'<span style="color: #ff9800;">[{time_str}] 系统: {message}</span>'
        else:
            formatted_msg = f'<b>{nickname}</b> <span style="color: #666;">[{time_str}]</span>: {message}'

        self.message_display.append(formatted_msg)

        # 自动滚动到底部
        cursor = self.message_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.message_display.setTextCursor(cursor)

        # 未读消息计数
        if not self.isVisible():
            self.unread_count += 1
            self.update_tab_title()

    def on_user_list_received(self, users, count):
        """用户列表更新回调"""
        self.user_list_widget.clear()
        self.user_list_widget.addItems(users)
        self.user_count_label.setText(f"在线用户: {count}")

    def append_system_message(self, message):
        """添加系统消息"""
        time_str = datetime.now().strftime('%H:%M:%S')
        formatted_msg = f'<span style="color: #ff9800;">[{time_str}] 系统: {message}</span>'
        self.message_display.append(formatted_msg)

    def update_tab_title(self):
        """更新标签页标题"""
        if self.parent_tab_widget:
            base_title = "💬 消息广播"
            if self.unread_count > 0:
                base_title += f" ({self.unread_count})"

            # 查找当前标签页索引
            for i in range(self.parent_tab_widget.count()):
                if self.parent_tab_widget.widget(i) == self:
                    self.parent_tab_widget.setTabText(i, base_title)
                    break

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        self.unread_count = 0
        self.update_tab_title()
        self.hide_main_log_area()

    def closeEvent(self, event):
        """关闭事件"""
        self.service.stop()
        super().closeEvent(event)

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()
