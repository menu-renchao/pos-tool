# lan_chat_tab.py
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QLabel, QListWidget, QSplitter, QCheckBox)

from pos_tool_new.base_tab import BaseTabWidget
from pos_tool_new.utils.app_config_utils import get_app_config_value, set_app_config_value


class LanChatTab(BaseTabWidget):
    # 信号定义
    message_received = pyqtSignal(str, str, object)
    connected = pyqtSignal()
    disconnected = pyqtSignal(int, str)
    user_list_received = pyqtSignal(object, int)
    system_message = pyqtSignal(str)
    connection_status_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__('💬 消息广播', parent)
        self.parent_tab_widget = parent.tabs if hasattr(parent, 'tabs') else None
        self.unread_count = 0
        self.is_connected = False

        # 读取 server_url 和昵称
        ip = get_app_config_value('micro_default_ip', '127.0.0.1')
        server_url = f"ws://{ip}:56789"
        nickname = get_app_config_value('lan_chat_nickname', '匿名用户')

        # 初始化服务
        from .lan_chat_service import LanChatService
        self.service = LanChatService(
            on_message_callback=self._emit_message_received,
            server_url=server_url
        )
        self.service.set_callbacks(
            on_connected=self._emit_connected,
            on_disconnected=self._emit_disconnected,
            on_user_list=self._emit_user_list_received
        )
        self._init_nickname = nickname
        self.init_ui()
        self.setup_connections()
        try:
            self.service.set_nickname(nickname)
            self.service.start()
        except Exception as e:
            self._emit_system_message(f"无法连接到聊天服务器: {e}")

        # 信号连接到主线程UI槽
        self.message_received.connect(self.on_message_received)
        self.connected.connect(self.on_connected)
        self.disconnected.connect(self.on_disconnected)
        self.user_list_received.connect(self.on_user_list_received)
        self.system_message.connect(self.append_system_message)

    def _emit_message_received(self, nickname, message, timestamp):
        try:
            self.message_received.emit(nickname, message, timestamp)
        except Exception as e:
            pass

    def _emit_connected(self):
        try:
            self.connected.emit()
        except Exception:
            pass

    def _emit_disconnected(self, code, reason):
        try:
            self.disconnected.emit(code, reason)
        except Exception:
            pass

    def _emit_user_list_received(self, users, count):
        try:
            self.user_list_received.emit(users, count)
        except Exception:
            pass

    def _emit_system_message(self, message):
        try:
            self.system_message.emit(message)
        except Exception:
            pass

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

        # 重连按钮
        self.reconnect_btn = QPushButton("重连")
        self.reconnect_btn.setMaximumWidth(50)
        self.reconnect_btn.setToolTip("手动重连聊天服务器")
        self.reconnect_btn.setEnabled(False)

        # 昵称设置
        nick_layout = QHBoxLayout()
        nick_layout.setSpacing(5)  # 缩小间距
        nick_label = QLabel("昵称:")
        self.nickname_edit = QLineEdit(self._init_nickname)
        self.nickname_edit.setMaximumWidth(120)
        self.set_nickname_btn = QPushButton("设置")
        self.set_nickname_btn.setMaximumWidth(50)
        nick_layout.addWidget(nick_label)
        nick_layout.addWidget(self.nickname_edit)
        nick_layout.addWidget(self.set_nickname_btn)
        nick_layout.addStretch(1)  # 让昵称输入框和按钮靠近

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.reconnect_btn)
        status_layout.addStretch()
        status_layout.addWidget(self.user_count_label)
        status_layout.addLayout(nick_layout)

        return status_layout

    def create_input_area(self):
        """创建输入区域"""
        input_layout = QHBoxLayout()

        # 新增：跑马灯显示复选框，默认不勾选
        self.marquee_checkbox = QCheckBox("跑马灯显示")
        self.marquee_checkbox.setChecked(False)
        input_layout.addWidget(self.marquee_checkbox)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setStyleSheet("""""")

        self.send_btn = QPushButton("发送")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            QLineEdit {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        
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
        self.reconnect_btn.clicked.connect(self.on_reconnect_clicked)
        # 输入状态检测
        self.message_input.textChanged.connect(self.on_text_changed)

    def on_reconnect_clicked(self):
        """手动重连按钮点击事件"""
        self._emit_system_message("正在尝试手动重连...")
        self.service.reconnect()
        self.reconnect_btn.setEnabled(False)

    def set_nickname(self):
        """设置昵称并持久化，禁止设置为“系统”"""
        nickname = self.nickname_edit.text().strip()
        if nickname == '系统':
            self._emit_system_message("昵称不能为‘系统’！请更换昵称。")
            return
        if nickname:
            self.service.set_nickname(nickname)
            set_app_config_value('lan_chat_nickname', nickname)
            self._emit_system_message(f"昵称已更改为: {nickname}")

    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if message and self.is_connected:
            marquee = self.marquee_checkbox.isChecked() if hasattr(self, 'marquee_checkbox') else False
            self.service.send_message(message, marquee=marquee)
            self.message_input.clear()
            self.stop_typing_indicator()
            if marquee:
                main_win = self.window()
                if hasattr(main_win, 'update_marquee_message'):
                    main_win.update_marquee_message(message)

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
        self.reconnect_btn.setEnabled(False)
        self.append_system_message("已连接到聊天服务器")
        self.connection_status_changed.emit(True)

    def on_disconnected(self, code, reason):
        """连接断开回调"""
        self.is_connected = False
        self.status_label.setText("连接断开")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.send_btn.setEnabled(False)
        self.reconnect_btn.setEnabled(True)
        self.append_system_message("与聊天服务器的连接已断开")
        self.connection_status_changed.emit(False)

    def on_message_received(self, nickname, message, timestamp):
        """收到消息回调"""
        from datetime import datetime
        if isinstance(timestamp, str):
            try:
                time_obj = datetime.fromisoformat(timestamp)
            except Exception:
                time_obj = datetime.now()
        else:
            time_obj = datetime.fromtimestamp(timestamp)
        time_str = time_obj.strftime('%H:%M:%S')

        # 系统消息只显示在消息区，不推送到跑马灯
        if nickname == '系统' or not message.strip():
            formatted_msg = f'<span style="color: #ff9800;">[{time_str}] 系统: {message}</span>'
            self.message_display.append(formatted_msg)
            return
        # latest_user_message 只显示内容到跑马灯，不显示在消息区
        elif nickname == '':
            main_win = self.window()
            if hasattr(main_win, 'update_marquee_message') and message.strip():
                main_win.update_marquee_message(message)
            return
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
