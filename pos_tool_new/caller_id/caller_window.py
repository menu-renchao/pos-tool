# caller_window.py
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QLabel, QComboBox, QLineEdit, QCheckBox,
                             QPushButton, QMessageBox,
                             QHBoxLayout, QVBoxLayout, QGroupBox, QGridLayout)

from pos_tool_new.caller_id.caller_service import CallerService
from pos_tool_new.main import BaseTabWidget


class CallerIdTabWidget(BaseTabWidget):
    """Caller ID 模拟拨号选项卡 - 紧凑优化版"""

    def __init__(self, parent=None):
        super().__init__("Caller ID 模拟拨号", parent)
        self.parent_window = parent
        self.setup_ui()
        self.service = CallerService()

    def setup_ui(self):
        # 设置全局字体
        font = QFont()
        font.setPointSize(9)  # 缩小字体
        self.setFont(font)

        # 创建主布局容器
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        main_layout.setSpacing(8)  # 减少间距

        # 使用网格布局合并所有设置
        grid_group = QGroupBox("拨号设置")
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(8, 12, 8, 12)  # 减少内边距
        grid_layout.setSpacing(8)  # 减少间距
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)

        # 主机地址
        host_label = QLabel("主机地址:")
        host_label.setStyleSheet("font-weight: bold;")
        self.host_ip = QComboBox()
        self.host_ip.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_ip.setEditable(True)
        self.host_ip.setCurrentText("192.168.0.")
        self.host_ip.setFixedHeight(28)  # 固定高度
        self.host_ip.setMaximumWidth(140)

        grid_layout.addWidget(host_label, 0, 0)
        grid_layout.addWidget(self.host_ip, 0, 1, 1, 2)

        # 用户姓名
        name_label = QLabel("用户姓名:")
        name_label.setStyleSheet("font-weight: bold;")
        self.name_input = QLineEdit("Meneu Sifu")
        self.name_input.setFixedHeight(28)  # 固定高度
        self.random_name = QCheckBox("随机生成")
        self.random_name.setChecked(True)
        self.random_name.setFixedHeight(28)  # 固定高度

        grid_layout.addWidget(name_label, 1, 0)
        grid_layout.addWidget(self.name_input, 1, 1)
        grid_layout.addWidget(self.random_name, 1, 2)

        # 电话号码
        phone_label = QLabel("电话号码:")
        phone_label.setStyleSheet("font-weight: bold;")
        self.phone_input = QLineEdit("8888098867")
        self.phone_input.setFixedHeight(28)  # 固定高度
        self.random_phone = QCheckBox("随机生成")
        self.random_phone.setChecked(True)
        self.random_phone.setFixedHeight(28)  # 固定高度

        grid_layout.addWidget(phone_label, 2, 0)
        grid_layout.addWidget(self.phone_input, 2, 1)
        grid_layout.addWidget(self.random_phone, 2, 2)

        # 拨号路线
        route_label = QLabel("拨号路线:")
        route_label.setStyleSheet("font-weight: bold;")
        self.route_combo = QComboBox()
        self.route_combo.addItems(["01", "02", "03"])
        self.route_combo.setCurrentText("01")
        self.route_combo.setFixedHeight(28)  # 固定高度
        self.use_real_time = QCheckBox("使用当前真实时间")
        self.use_real_time.setChecked(True)
        self.use_real_time.setFixedHeight(28)  # 固定高度

        grid_layout.addWidget(route_label, 3, 0)
        grid_layout.addWidget(self.route_combo, 3, 1)
        grid_layout.addWidget(self.use_real_time, 3, 2)

        grid_group.setLayout(grid_layout)
        main_layout.addWidget(grid_group)

        # 拨号按钮
        self.dial_button = QPushButton("模拟拨号")
        self.dial_button.setFixedHeight(32)  # 缩小高度
        self.dial_button.clicked.connect(self.on_dial)

        # 按钮居中
        button_container = QHBoxLayout()
        button_container.addStretch()
        button_container.addWidget(self.dial_button)
        button_container.addStretch()
        button_container.setContentsMargins(0, 4, 0, 4)  # 减少边距

        main_layout.addLayout(button_container)
        main_layout.addStretch(1)

        # 设置主布局
        self.layout.addLayout(main_layout)

    def on_dial(self):
        """模拟拨号逻辑"""
        try:
            host = self.host_ip.currentText()
            name = self.name_input.text()
            phone = self.phone_input.text()
            route = self.route_combo.currentText()
            use_real_time = self.use_real_time.isChecked()
            random_name = self.random_name.isChecked()
            random_phone = self.random_phone.isChecked()

            # 格式化电话号码
            formatted_number = CallerService.format_phone_number(phone)

            # 选择时间格式
            time_str = CallerService.get_current_time_formatted() if use_real_time else CallerService.get_random_time_formatted()

            # 生成数据包
            packet = CallerService.generate_packet(name, formatted_number)

            # 发送 UDP 包
            CallerService.send_udp_packet(packet, host)

            # 记录日志
            log_message = f"{route} I S 0000 G A1 {time_str}   {formatted_number}   {name}"

            # 随机生成姓名或号码（如果需要）
            if random_name:
                self.name_input.setText(CallerService.generate_random_name())
            if random_phone:
                self.phone_input.setText(CallerService.generate_random_phone_number())

            self.service.log(f"发送消息成功: {log_message}", "success")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"主机 POS 没开或端口被占用: {str(e)}")

    def set_host_ip(self, ip: str):
        """同步设置主机IP到host_ip输入框"""
        if self.host_ip:
            self.host_ip.setCurrentText(ip)
