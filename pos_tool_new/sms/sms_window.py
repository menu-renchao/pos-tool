from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QToolButton, QSizePolicy)
from PyQt6.QtCore import Qt
import pyperclip

from pos_tool_new.main import BaseTabWidget
from pos_tool_new.work_threads import SmsWorkerThread


class SmsWindow(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__("短信验证码", parent)
        self.worker_thread = SmsWorkerThread()
        self.init_ui()
        self.connect_signals()
        self.worker_thread.phone_numbers_ready.connect(self.handle_phone_numbers_ready)
        self.worker_thread.messages_ready.connect(self.handle_messages_ready)
        self.refresh_phone_numbers()

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 查询条件区域（手机号、关键词、数量、按钮一行显示）
        condition_group = QWidget()
        condition_layout = QHBoxLayout(condition_group)
        condition_layout.setContentsMargins(0, 0, 0, 0)
        condition_layout.setSpacing(10)

        phone_label = QLabel("手机号:")
        phone_label.setFixedWidth(40)
        condition_layout.addWidget(phone_label)
        self.phone_combo = QComboBox()
        self.phone_combo.addItem("请选择手机号")
        self.phone_combo.setFixedWidth(140)
        condition_layout.addWidget(self.phone_combo)
        self.copy_phone_btn = QPushButton("复制手机号")
        self.copy_phone_btn.setFixedWidth(80)
        condition_layout.addWidget(self.copy_phone_btn)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(60)
        condition_layout.addWidget(self.refresh_btn)
        keyword_label = QLabel("关键词:")
        keyword_label.setFixedWidth(40)
        condition_layout.addWidget(keyword_label)
        self.keyword_combo = QComboBox()
        self.keyword_combo.setEditable(True)
        self.keyword_combo.addItem("输入关键词")
        # 预填关键词
        for kw in ["Menusifu", "authentication", "Restaurant", "code"]:
            self.keyword_combo.addItem(kw)
        self.keyword_combo.setFixedWidth(120)
        condition_layout.addWidget(self.keyword_combo)
        count_label = QLabel("数量:")
        count_label.setFixedWidth(40)
        condition_layout.addWidget(count_label)
        self.count_combo = QComboBox()
        self.count_combo.addItems([str(i) for i in range(1, 16)])
        self.count_combo.setCurrentIndex(0)
        self.count_combo.setFixedWidth(60)
        condition_layout.addWidget(self.count_combo)
        self.query_btn = QPushButton("查询短信")
        self.query_btn.setFixedWidth(90)
        condition_layout.addWidget(self.query_btn)
        main_layout.addWidget(condition_group)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setMinimumHeight(20)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        # 短信表格
        self.message_table = QTableWidget(0, 4)
        self.message_table.setHorizontalHeaderLabels(["发送人", "时间", "内容", "操作"])
        header = self.message_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.message_table.setColumnWidth(0, 100)
        self.message_table.setColumnWidth(1, 120)
        self.message_table.setColumnWidth(3, 80)
        self.message_table.setWordWrap(True)
        self.message_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.message_table)

        # 清空按钮区域
        clear_group = QWidget()
        clear_layout = QHBoxLayout(clear_group)
        clear_layout.setContentsMargins(0, 0, 0, 0)
        clear_layout.addStretch(1)
        self.clear_btn = QToolButton()
        self.clear_btn.setText("清空")
        self.clear_btn.setFixedWidth(80)
        clear_layout.addWidget(self.clear_btn)
        clear_layout.addStretch(1)
        main_layout.addWidget(clear_group)

        # 设置主布局
        self.layout.addLayout(main_layout)

    def connect_signals(self):
        self.copy_phone_btn.clicked.connect(self.copy_phone_number)
        self.refresh_btn.clicked.connect(self.refresh_phone_numbers)
        self.query_btn.clicked.connect(self.query_messages)
        self.clear_btn.clicked.connect(self.clear_messages)

    def copy_phone_number(self):
        current_phone = self.phone_combo.currentText().strip()
        if current_phone and current_phone != "请选择手机号":
            # 如果是+1开头，去掉+1和空格，只复制后面的号码
            if current_phone.startswith("+1 "):
                phone_to_copy = current_phone[3:].strip()
            elif current_phone.startswith("+1") and len(current_phone) > 2 and current_phone[2].isdigit():
                phone_to_copy = current_phone[2:].strip()
            else:
                phone_to_copy = current_phone
            pyperclip.copy(phone_to_copy)
            self.status_label.setText(f"已复制手机号: {phone_to_copy}")
        else:
            self.status_label.setText("未复制，请选择有效手机号")

    def refresh_phone_numbers(self):
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait(500)
        self.status_label.setText("正在刷新手机号...")
        self.refresh_btn.setEnabled(False)
        self.worker_thread.set_refresh_operation()
        self.worker_thread.start()

    def handle_phone_numbers_ready(self, phone_numbers, error):
        self.refresh_btn.setEnabled(True)
        if error:
            self.status_label.setText(f'<span style="color:#e74c3c;">{error}</span>')
            self.status_label.setTextFormat(Qt.TextFormat.RichText)
            return
        current_index = self.phone_combo.currentIndex()
        self.phone_combo.clear()
        self.phone_combo.addItem("请选择手机号")
        self.phone_combo.addItems(phone_numbers)
        if 0 <= current_index < self.phone_combo.count():
            self.phone_combo.setCurrentIndex(current_index)
        self.status_label.setText(f"已刷新 {len(phone_numbers)} 个手机号")

    def query_messages(self):
        phone_number = self.phone_combo.currentText()
        keyword = self.keyword_combo.currentText()
        count = int(self.count_combo.currentText())
        if phone_number == "请选择手机号" or not phone_number:
            self.status_label.setText("请选择手机号")
            return
        # 如果没选择关键词（即为“输入关键词”且内容为空），则不做匹配
        if (self.keyword_combo.currentIndex() == 0 and not keyword.strip()):
            keyword = " "
        elif keyword == "输入关键词" or not keyword:
            keyword = " "
        if self.worker_thread.isRunning():
            self.worker_thread.terminate()
        self.status_label.setText(f"正在查询 {phone_number} 的短信...")
        self.query_btn.setEnabled(False)
        self.worker_thread.set_query_operation(phone_number, keyword, count)
        self.worker_thread.start()

    def handle_messages_ready(self, messages, error):
        self.query_btn.setEnabled(True)
        if error:
            self.status_label.setText(error)
            return
        self.message_table.setRowCount(0)
        for msg in messages:
            row_position = self.message_table.rowCount()
            self.message_table.insertRow(row_position)
            sender_item = QTableWidgetItem(msg['sender'])
            sender_item.setFlags(sender_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.message_table.setItem(row_position, 0, sender_item)
            time_item = QTableWidgetItem(msg['time'])
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.message_table.setItem(row_position, 1, time_item)
            content_item = QTableWidgetItem(msg['content'])
            content_item.setFlags(content_item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.message_table.setItem(row_position, 2, content_item)
            btn_copy = QPushButton("复制")
            btn_copy.setFixedSize(60, 25)
            btn_copy.setStyleSheet("font-size: 12px;")
            btn_copy.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.addStretch(1)
            cell_layout.addWidget(btn_copy)
            cell_layout.addStretch(1)
            self.message_table.setCellWidget(row_position, 3, cell_widget)
            btn_copy.clicked.connect(lambda _, r=row_position: self.copy_row_data(r))
        self.status_label.setText(f"找到 {len(messages)} 条匹配短信")
        self.message_table.scrollToBottom()

    def clear_messages(self):
        self.message_table.setRowCount(0)
        self.status_label.setText("已清空短信列表")

    def copy_row_data(self, r):
        item = self.message_table.item(r, 2)
        text_to_copy = self.extract_verification_code(item.text())
        if text_to_copy:
            pyperclip.copy(text_to_copy)
            self.status_label.setText(f"已复制验证码: {text_to_copy}")
        else:
            self.status_label.setText("未找到验证码")

    def extract_verification_code(self, text):
        import re
        patterns = [
            r'(?:验证码|code)[：:]\s*(\d{4,6})',
            r'(?<!\d)(\d{4,6})(?!\d)',
            r'(\d{4,6})(?=[^\d]|$)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()