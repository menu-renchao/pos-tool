from PyQt6.QtWidgets import (QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QRadioButton, QButtonGroup, QComboBox,
                             QWidget, QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt
from pos_tool_new.main import BaseTabWidget
from .generate_img_service import GenerateImgService
from ..work_threads import GenerateImgThread


class GenerateImgTabWidget(BaseTabWidget):
    def __init__(self, title="图片生成", parent=None):
        super().__init__(title, parent)
        self.service = GenerateImgService()
        self.thread = None
        self.init_ui()

    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # 添加各个功能模块
        main_layout.addWidget(self.create_dimension_section())
        main_layout.addWidget(self.create_size_section())
        main_layout.addWidget(self.create_format_section())
        main_layout.addWidget(self.create_button_section())
        main_layout.addWidget(self.create_status_section())

        self.layout.addLayout(main_layout)
        self.update_mode()

    def create_dimension_section(self):
        """创建尺寸输入区域"""
        self.dim_group_box = QGroupBox("按长宽生成")
        layout = QHBoxLayout()

        # 模式选择
        self.radio_dim = QRadioButton("按长宽")
        self.radio_dim.setChecked(True)
        layout.addWidget(self.radio_dim)

        # 宽度输入
        layout.addWidget(QLabel("宽度:"))
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("宽度")
        self.width_input.setMaximumWidth(80)
        layout.addWidget(self.width_input)

        # 高度输入
        layout.addWidget(QLabel("高度:"))
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("高度")
        self.height_input.setMaximumWidth(80)
        layout.addWidget(self.height_input)

        layout.addStretch()
        self.dim_group_box.setLayout(layout)

        return self.dim_group_box

    def create_size_section(self):
        """创建大小输入区域"""
        self.size_group_box = QGroupBox("按大小生成")
        layout = QHBoxLayout()

        # 模式选择
        self.radio_size = QRadioButton("按大小")
        layout.addWidget(self.radio_size)

        # 大小输入
        layout.addWidget(QLabel("大小:"))
        self.mb_input = QLineEdit()
        self.mb_input.setMaximumWidth(80)
        layout.addWidget(self.mb_input)
        layout.addWidget(QLabel("MB"))

        layout.addStretch()
        self.size_group_box.setLayout(layout)

        # 设置按钮组
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_dim)
        self.mode_group.addButton(self.radio_size)
        self.radio_dim.toggled.connect(self.update_mode)

        return self.size_group_box

    def create_format_section(self):
        """创建格式选择区域"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("图片格式:"))
        self.format_box = QComboBox()
        self.format_box.addItems(["BMP", "PNG", "JPEG"])
        self.format_box.setMaximumWidth(120)
        layout.addWidget(self.format_box)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_button_section(self):
        """创建按钮区域"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.gen_btn = QPushButton("生成图片")
        self.gen_btn.clicked.connect(self.generate_img)
        self.gen_btn.setFixedSize(100, 30)

        layout.addStretch()
        layout.addWidget(self.gen_btn)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_status_section(self):
        """创建状态显示区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumHeight(25)
        self.status_label.setStyleSheet("""
            QLabel { 
                color: #666; 
                padding: 3px;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-size: 12px;
            }
        """)

        layout.addWidget(self.status_label)
        widget.setLayout(layout)
        return widget

    def update_mode(self):
        """更新模式显示状态"""
        is_size_mode = self.radio_size.isChecked()

        # 更新输入框状态
        self.width_input.setDisabled(is_size_mode)
        self.height_input.setDisabled(is_size_mode)
        self.mb_input.setDisabled(not is_size_mode)

        # 更新分组框样式
        if is_size_mode:
            self.dim_group_box.setStyleSheet("QGroupBox { color: #999; }")
            self.size_group_box.setStyleSheet("QGroupBox { color: #000; font-weight: bold; }")
            self.status_label.setText("当前模式：按大小生成")
        else:
            self.dim_group_box.setStyleSheet("QGroupBox { color: #000; font-weight: bold; }")
            self.size_group_box.setStyleSheet("QGroupBox { color: #999; }")
            self.status_label.setText("当前模式：按长宽生成")

    def generate_img(self):
        """生成图片"""
        mode = "size" if self.radio_size.isChecked() else "dim"
        width = self.width_input.text().strip()
        height = self.height_input.text().strip()
        mb = self.mb_input.text().strip()
        fmt = self.format_box.currentText()

        # 输入验证
        if mode == "dim" and (not width or not height):
            self.status_label.setText("请输入宽度和高度")
            return
        if mode == "size" and not mb:
            self.status_label.setText("请输入图片大小")
            return

        self.status_label.setText("生成中，请稍候...")
        self.gen_btn.setDisabled(True)

        self.thread = GenerateImgThread(self.service, mode, width, height, mb, fmt)
        self.thread.finished_signal.connect(self.on_generate_finished)
        self.thread.start()

    def log_to_mainwindow(self, msg):
        main_win = self.window()
        if hasattr(main_win, 'append_log'):
            main_win.append_log(msg)
        else:
            print(msg)

    def on_generate_finished(self, output_path):
        """生成完成回调"""
        self.gen_btn.setDisabled(False)

        if output_path:
            msg = f"生成成功: {output_path}"
            self.status_label.setText("生成成功！")
            self.status_label.setStyleSheet("""
                QLabel { 
                    color: green; 
                    font-weight: bold;
                    background-color: #f0f9f0;
                    border: 1px solid #4CAF50;
                    border-radius: 3px;
                    font-size: 12px;
                }
            """)
        else:
            msg = "生成失败"
            self.status_label.setText("生成失败")
            self.status_label.setStyleSheet("""
                QLabel { 
                    color: red; 
                    font-weight: bold;
                    background-color: #fdf0f0;
                    border: 1px solid #f44336;
                    border-radius: 3px;
                    font-size: 12px;
                }
            """)

        self.log_to_mainwindow(msg)