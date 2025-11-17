from typing import Optional, List
import copy

import copy
from typing import Optional, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QComboBox, QGroupBox, QFormLayout, QAbstractItemView, QSizePolicy
)

from pos_tool_new.linux_file_config.file_config_linux_service import FileConfigService, FileConfigItem, KeyValueItem
from pos_tool_new.main import BaseTabWidget, MainWindow
from pos_tool_new.work_threads import FileConfigModifyThread


class KeyValueEditDialog(QDialog):
    """键值对编辑对话框"""

    def __init__(self, key_value_item: Optional[KeyValueItem] = None, parent=None):
        super().__init__(parent)
        self.key_value_item = key_value_item or KeyValueItem(key="")
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle("编辑键值对配置")
        self.setMinimumWidth(900)

        layout = QVBoxLayout(self)

        # 键名输入
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("键名:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入配置键名，如：api.url")
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)

        # 环境输入框竖直对齐
        env_layout = QVBoxLayout()
        # QA
        qa_layout = QHBoxLayout()
        qa_layout.addWidget(QLabel("    QA:"))
        self.qa_edit = QLineEdit()
        self.qa_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        qa_layout.addWidget(self.qa_edit)
        env_layout.addLayout(qa_layout)
        # PROD
        prod_layout = QHBoxLayout()
        prod_layout.addWidget(QLabel("PROD:"))
        self.prod_edit = QLineEdit()
        self.prod_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        prod_layout.addWidget(self.prod_edit)
        env_layout.addLayout(prod_layout)
        # DEV
        dev_layout = QHBoxLayout()
        dev_layout.addWidget(QLabel("  DEV:"))
        self.dev_edit = QLineEdit()
        self.dev_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        dev_layout.addWidget(self.dev_edit)
        env_layout.addLayout(dev_layout)
        layout.addLayout(env_layout)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_data(self):
        """加载数据到界面"""
        self.key_edit.setText(self.key_value_item.key)
        self.qa_edit.setText(self.key_value_item.qa_value)
        self.prod_edit.setText(self.key_value_item.prod_value)
        self.dev_edit.setText(self.key_value_item.dev_value)

    def get_key_value_item(self) -> KeyValueItem:
        """获取编辑后的键值对项"""
        return KeyValueItem(
            key=self.key_edit.text().strip(),
            qa_value=self.qa_edit.text().strip(),
            prod_value=self.prod_edit.text().strip(),
            dev_value=self.dev_edit.text().strip()
        )


class FileConfigEditDialog(QDialog):
    """文件配置编辑对话框"""

    def __init__(self, config_item: Optional[FileConfigItem] = None, parent=None):
        super().__init__(parent)
        # 使用深拷贝，确保编辑时不影响主数据
        self.config_item = copy.deepcopy(config_item) if config_item else FileConfigItem(name="", file_path="",
                                                                                         key_values=[])
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle("编辑文件配置")
        self.setMinimumWidth(900)

        layout = QVBoxLayout(self)

        # 配置名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("配置名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入配置项名称")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # 文件路径
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("文件路径:"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("相对路径，如：kpos/front/js/cloudUrlConfig.json")
        path_layout.addWidget(self.path_edit)
        layout.addLayout(path_layout)

        # 键值对列表
        layout.addWidget(QLabel("键值对配置:"))
        self.key_value_table = QTableWidget()
        self.key_value_table.setColumnCount(2)
        self.key_value_table.setHorizontalHeaderLabels(["键名", "值"])
        self.key_value_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.key_value_table.setColumnWidth(0, 120)
        self.key_value_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.key_value_table)

        # 键值对操作按钮
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.add_btn.clicked.connect(self.add_key_value)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_key_value)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_key_value)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 对话框按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 连接信号
        self.key_value_table.itemSelectionChanged.connect(self.on_selection_changed)

    def load_data(self):
        """加载数据到界面"""
        self.name_edit.setText(self.config_item.name)
        self.path_edit.setText(self.config_item.file_path)
        self.refresh_key_value_table()

    def refresh_key_value_table(self):
        """刷新键值对表格"""
        self.key_value_table.setRowCount(0)

        for i, kv_item in enumerate(self.config_item.key_values):
            self.key_value_table.insertRow(i)
            # 键名
            self.key_value_table.setItem(i, 0, QTableWidgetItem(kv_item.key))

            # 环境值（用QLabel实现自动换行）
            value_text = f"QA: {kv_item.qa_value}\nPROD: {kv_item.prod_value}\nDEV: {kv_item.dev_value}"
            value_label = QLabel(value_text)
            value_label.setWordWrap(True)
            value_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.key_value_table.setCellWidget(i, 1, value_label)
            self.key_value_table.setRowHeight(i, 60)  # 可根据实际内容调整高度

    def on_selection_changed(self):
        """选择变化时更新按钮状态"""
        has_selection = len(self.key_value_table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def add_key_value(self):
        """新增键值对"""
        dialog = KeyValueEditDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_item = dialog.get_key_value_item()
            if new_item.key:  # 确保键名不为空
                self.config_item.key_values.append(new_item)
                self.refresh_key_value_table()

    def edit_key_value(self):
        """编辑选中的键值对"""
        selected_rows = set(item.row() for item in self.key_value_table.selectedItems())
        if not selected_rows:
            return

        row = list(selected_rows)[0]
        if row < len(self.config_item.key_values):
            dialog = KeyValueEditDialog(self.config_item.key_values[row])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.config_item.key_values[row] = dialog.get_key_value_item()
                self.refresh_key_value_table()

    def edit_key_value_at_index(self, index: int):
        """编辑指定索引的键值对"""
        if 0 <= index < len(self.config_item.key_values):
            dialog = KeyValueEditDialog(self.config_item.key_values[index])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.config_item.key_values[index] = dialog.get_key_value_item()
                self.refresh_key_value_table()

    def delete_key_value(self):
        """删除选中的键值对"""
        selected_rows = set(item.row() for item in self.key_value_table.selectedItems())
        if not selected_rows:
            return

        # 按倒序删除避免索引问题
        for row in sorted(selected_rows, reverse=True):
            if 0 <= row < len(self.config_item.key_values):
                del self.config_item.key_values[row]

        self.refresh_key_value_table()

    def get_config_item(self) -> FileConfigItem:
        """获取编辑后的配置项"""
        return FileConfigItem(
            name=self.name_edit.text().strip(),
            file_path=self.path_edit.text().strip(),
            key_values=self.config_item.key_values.copy(),
            enabled=True
        )


class FileConfigTabWidget(BaseTabWidget):
    """文件配置管理选项卡"""

    def __init__(self, parent: Optional[MainWindow] = None):
        super().__init__("文件配置管理")
        self.parent_window = parent
        self.service = FileConfigService()

        # SSH连接控件
        self.host_ip: Optional[QComboBox] = None
        self.username: Optional[QLineEdit] = None
        self.password: Optional[QLineEdit] = None
        self.env_group = None

        # 配置列表控件
        self.config_table: Optional[QTableWidget] = None

        self.setup_ui()
        self.refresh_config_list()

    def setup_ui(self):
        # 主布局 - 使用更紧凑的间距
        main_layout = self.layout
        main_layout.setSpacing(6)  # 减少间距
        main_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距

        # SSH连接组 - 紧凑样式
        ssh_group = QGroupBox("SSH连接设置")
        ssh_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 11px; 
                margin-top: 6px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 0 0 0;
            }
        """)
        ssh_layout = QHBoxLayout(ssh_group)
        ssh_layout.setSpacing(6)  # 减少间距
        ssh_layout.setContentsMargins(6, 8, 6, 6)  # 减少内边距

        # 主机IP
        host_label = QLabel("主机IP:")
        host_label.setStyleSheet("font-size: 11px;")
        self.host_ip = QComboBox()
        self.host_ip.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_ip.setEditable(True)
        self.host_ip.setFixedWidth(120)
        self.host_ip.setStyleSheet("QComboBox { padding: 3px; font-size: 11px; }")
        ssh_layout.addWidget(host_label)
        ssh_layout.addWidget(self.host_ip)

        # 环境选择
        env_frame, self.env_group = self.create_env_selector("QA")
        env_frame.setFixedWidth(200)
        ssh_layout.addWidget(env_frame)

        # 用户名
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-size: 11px;")
        self.username = QLineEdit("menu")
        self.username.setFixedWidth(100)
        self.username.setStyleSheet("QLineEdit { padding: 3px; font-size: 11px; }")
        ssh_layout.addWidget(username_label)
        ssh_layout.addWidget(self.username)

        # 密码
        password_label = QLabel("密码:")
        password_label.setStyleSheet("font-size: 11px;")
        self.password = QLineEdit("M2ei#a$19!")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedWidth(100)
        self.password.setStyleSheet("QLineEdit { padding: 3px; font-size: 11px; }")
        ssh_layout.addWidget(password_label)
        ssh_layout.addWidget(self.password)

        # 重启POS按钮
        self.restart_btn = QPushButton("重启pos")
        self.restart_btn.setToolTip("重启POS服务，可能耗时1-4分钟")
        self.restart_btn.setFixedWidth(100)
        self.restart_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.restart_btn.clicked.connect(self.on_restart_pos_linux)
        ssh_layout.addWidget(self.restart_btn)

        ssh_layout.addStretch()
        main_layout.addWidget(ssh_group)

        # 配置列表组 - 紧凑样式
        config_group = QGroupBox("文件配置列表")
        config_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 11px; 
                margin-top: 6px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)

        # 关键修改：直接创建 QVBoxLayout 并设置给 config_group
        config_layout = QVBoxLayout(config_group)  # 直接设置给 config_group
        config_layout.setSpacing(4)  # 减少间距
        config_layout.setContentsMargins(6, 8, 6, 6)  # 减少内边距

        # 操作按钮区域 - 紧凑样式
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)

        self.add_btn = QPushButton("新增配置")
        self.execute_all_btn = QPushButton("执行所有启用配置")
        self.reload_btn = QPushButton("重载配置文件")


        # 紧凑按钮样式
        button_style = """
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """

        self.add_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-color: #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.execute_all_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-color: #F57C00;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        self.reload_btn.setStyleSheet(button_style + """
                    QPushButton {
                        background-color: #58a787;
                        color: white;
                        border-color: #F57C00;
                    }
                    QPushButton:hover {
                        background-color: #F57C00;
                    }
                """)

        self.add_btn.clicked.connect(self.on_add_config)
        self.execute_all_btn.clicked.connect(self.on_execute_all_enabled)
        self.reload_btn.clicked.connect(self.reload_config)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.execute_all_btn)
        button_layout.addWidget(self.reload_btn)
        button_layout.addStretch()
        config_layout.addLayout(button_layout)

        # 配置表格 - 紧凑样式
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(5)
        self.config_table.setAlternatingRowColors(True)
        self.config_table.setHorizontalHeaderLabels(['启用', '配置名称', '文件路径', '键值对数量', '操作'])

        # 紧凑表格样式
        self.config_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: white;
                selection-color: black;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 2px 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: transparent;
                color: black;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 4px;
                border: none;
                font-size: 11px;
                font-weight: bold;
            }
            QTableWidget::item:selected {
    background-color: #CCE8FF;  /* 选中行高亮色，可自定义 */
}
QTableWidget::item:focus {
    background-color: #CCE8FF;
}
QTableWidget::item {
    selection-background-color: #CCE8FF;
}
        """)

        # 设置表格选择行为
        self.config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.config_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # 设置表格尺寸策略
        self.config_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 设置列宽比例 - 更紧凑的列宽
        header = self.config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 启用列
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 配置名称
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 文件路径
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 键值对数量
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 操作列

        # 设置固定列宽 - 减小宽度
        self.config_table.setColumnWidth(0, 50)  # 启用列
        self.config_table.setColumnWidth(3, 80)  # 键值对数量列

        self.config_table.verticalHeader().setVisible(False)
        self.config_table.itemSelectionChanged.connect(self.on_selection_changed)

        # 关键修改：将表格添加到布局并设置拉伸因子
        config_layout.addWidget(self.config_table, 1)  # 拉伸因子为1

        # 关键修改：将配置组添加到主布局并设置拉伸因子
        main_layout.addWidget(config_group, 1)  # 拉伸因子为1

    def refresh_config_list(self):
        """刷新配置列表"""
        self.config_table.setRowCount(0)
        configs = self.service.get_all_configs()

        for i, config in enumerate(configs):
            self.config_table.insertRow(i)

            # 启用复选框
            checkbox = QCheckBox()
            checkbox.setChecked(config.enabled)
            checkbox.stateChanged.connect(lambda state, cfg=config: self.on_toggle_enabled(cfg, state))
            checkbox.setStyleSheet("QCheckBox { margin-left: 5px; }")
            self.config_table.setCellWidget(i, 0, checkbox)

            # 配置名称
            name_item = QTableWidgetItem(config.name)
            name_item.setToolTip(config.name)
            name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self.config_table.setItem(i, 1, name_item)

            # 文件路径
            path_item = QTableWidgetItem(config.file_path)
            path_item.setToolTip(config.file_path)
            path_item.setFlags(path_item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self.config_table.setItem(i, 2, path_item)

            # 键值对数量（改为按钮，点击弹窗）
            kv_btn = QPushButton(str(len(config.key_values)))
            kv_btn.clicked.connect(lambda checked, cfg=config: self.on_show_detail(cfg))
            kv_btn.setStyleSheet('''
                QPushButton {
                    border: none; 
                    color: blue; 
                    text-decoration: underline; 
                    background: transparent;
                    font-size: 11px;
                    padding: 2px 4px;
                }
                QPushButton:hover {
                    color: darkblue;
                }
            ''')
            kv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.config_table.setCellWidget(i, 3, kv_btn)

            # 操作列 - 紧凑按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 1, 2, 1)  # 减少内边距
            action_layout.setSpacing(4)  # 减少间距

            # 修改按钮
            edit_btn = QPushButton("修改")
            edit_btn.clicked.connect(lambda checked, cfg=config: self.on_edit_config(cfg))
            edit_btn.setFixedSize(45, 24)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFC107;
                    color: black;
                    font-size: 10px;
                    padding: 2px 4px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #ffb300;
                }
            """)

            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, cfg=config: self.on_delete_config(cfg))
            delete_btn.setFixedSize(45, 24)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    font-size: 10px;
                    padding: 2px 4px;
                    border: 1px solid #d32f2f;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)

            # 执行按钮
            execute_btn = QPushButton("执行")
            execute_btn.clicked.connect(lambda checked, cfg=config: self.on_execute_single(cfg))
            execute_btn.setFixedSize(45, 24)
            execute_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 10px;
                    padding: 2px 4px;
                    border: 1px solid #45a049;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            action_layout.addWidget(execute_btn)
            action_layout.addStretch()

            self.config_table.setCellWidget(i, 4, action_widget)

            # 设置更小的行高
            self.config_table.setRowHeight(i, 30)  # 减小行高

    def on_selection_changed(self):
        """选择变化时更新按钮状态"""
        has_selection = len(self.config_table.selectionModel().selectedRows()) > 0
        self.execute_all_btn.setEnabled(has_selection)


    def on_toggle_enabled(self, config: FileConfigItem, state: int):
        """切换配置启用状态"""
        enabled = (state == Qt.CheckState.Checked.value)
        self.service.toggle_config_enabled(config.name, enabled)

    def on_add_config(self):
        """新增配置"""
        dialog = FileConfigEditDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config_item()
            if self.service.add_config(new_config):
                self.refresh_config_list()
                QMessageBox.information(self, "成功", "配置项添加成功")
            else:
                QMessageBox.warning(self, "错误", "配置项名称已存在")

    def on_edit_config(self, config: FileConfigItem):
        """编辑配置"""
        dialog = FileConfigEditDialog(config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_config_item()
            if self.service.update_config(config.name, new_config):
                self.refresh_config_list()
                QMessageBox.information(self, "成功", "配置项修改成功")
            else:
                QMessageBox.warning(self, "错误", "配置项修改失败")

    def on_delete_config(self, config: FileConfigItem):
        """删除配置"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除配置项 '{config.name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.service.delete_config(config.name):
                self.refresh_config_list()
                QMessageBox.information(self, "成功", "配置项删除成功")

    def on_show_detail(self, config: FileConfigItem):
        """显示配置详情"""
        dialog = FileConfigEditDialog(config)
        dialog.setMinimumSize(1000, 600)
        dialog.setWindowTitle(f"配置详情 - {config.name}")

        # 隐藏编辑控件
        dialog.name_edit.setVisible(False)
        dialog.path_edit.setVisible(False)
        dialog.add_btn.setVisible(False)
        dialog.edit_btn.setVisible(False)
        dialog.delete_btn.setVisible(False)

        # 隐藏操作列的按钮
        for i in range(dialog.key_value_table.rowCount()):
            widget = dialog.key_value_table.cellWidget(i, 5)
            if widget:
                widget.setVisible(False)

        dialog.exec()

    def _validate_connection_params(self) -> tuple:
        """验证连接数"""
        if not all([self.host_ip, self.username, self.password]):
            return False, "SSH连接参数未初始化", "", "", "", ""

        host = self.host_ip.currentText().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()
        env = self.get_selected_env(self.env_group)

        # 验证IP地址格式
        if not host or host.endswith('.') or len(host.split('.')) != 4:
            return False, "请填写完整的主机IP地址！", host, username, password, env

        ip_parts = host.split('.')
        for part in ip_parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                return False, "请填写有效的主机IP地址！", host, username, password, env

        if not username:
            return False, "请填写用户名！", host, username, password, env

        if not password:
            return False, "请填写密码！", host, username, password, env

        return True, "", host, username, password, env

    def on_execute_single(self, config: FileConfigItem):
        """执行单个配置"""
        is_valid, error_msg, host, username, password, env = self._validate_connection_params()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return

        if not config.enabled:
            QMessageBox.warning(self, "提示", "该配置项未启用，无法执行")
            return

        # 显示进度条
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat(f"正在执行配置: {config.name}")

        # 启动线程
        self.modify_thread = FileConfigModifyThread(
            self.service, host, username, password, config, env
        )

        self.modify_thread.progress_updated.connect(
            lambda percent: self.parent_window.progress_bar.setValue(percent) if self.parent_window else None
        )
        self.modify_thread.progress_text_updated.connect(
            lambda text: self.parent_window.progress_bar.setFormat(text) if self.parent_window else None
        )
        self.modify_thread.error_occurred.connect(
            lambda msg: QMessageBox.warning(self, "错误", msg)
        )
        self.modify_thread.finished_updated.connect(self.on_execute_finished)
        self.modify_thread.start()

    def on_execute_all_enabled(self):
        """执行所有启用的配置"""
        is_valid, error_msg, host, username, password, env = self._validate_connection_params()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return

        configs = self.service.get_all_configs()
        enabled_configs = [cfg for cfg in configs if cfg.enabled]

        if not enabled_configs:
            QMessageBox.warning(self, "提示", "没有启用的配置项")
            return

        reply = QMessageBox.question(
            self, "确认执行",
            f"确定要执行所有 {len(enabled_configs)} 个启用的配置项吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 批量执行
        self.execute_configs_batch(enabled_configs, host, username, password, env)

    def execute_configs_batch(self, configs: List[FileConfigItem], host: str,
                              username: str, password: str, env: str):
        """批量执行配置"""
        if not configs:
            return

        self.batch_configs = configs.copy()
        self.current_batch_index = 0
        self.batch_success_count = 0
        self.batch_failed_count = 0

        # 显示进度条
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, len(configs) * 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("批量执行配置中...")

        # 开始执行第一个配置
        self.execute_next_config_in_batch(host, username, password, env)

    def execute_next_config_in_batch(self, host: str, username: str, password: str, env: str):
        """执行批次的下一个配置"""
        if self.current_batch_index >= len(self.batch_configs):
            # 所有配置执行完成
            self.on_batch_execute_finished()
            return

        current_config = self.batch_configs[self.current_batch_index]
        current_index = self.current_batch_index

        # 更新进度文本
        if self.parent_window:
            self.parent_window.progress_bar.setFormat(
                f"执行配置 ({current_index + 1}/{len(self.batch_configs)}): {current_config.name}"
            )

        # 执行当前配置
        self.modify_thread = FileConfigModifyThread(
            self.service, host, username, password, current_config, env
        )

        self.modify_thread.progress_updated.connect(
            lambda percent: self.on_batch_progress_updated(current_index, percent)
        )
        # 修正信号连接，避免 lambda 捕获问题
        self.modify_thread.finished_updated.connect(self.on_single_config_finished)
        self.modify_thread.start()

    def on_batch_progress_updated(self, config_index: int, percent: int):
        """批量执行进度更新"""
        if self.parent_window:
            # 计算总体进度
            base_progress = config_index * 100
            current_progress = base_progress + percent
            self.parent_window.progress_bar.setValue(current_progress)

    def on_single_config_finished(self, success: bool, message: str):
        """单个配置执行完成"""
        if success:
            self.batch_success_count += 1
            self.service.log(f"配置执行成功: {message}", level="success")
        else:
            self.batch_failed_count += 1
            self.service.log(f"配置执行失败: {message}", level="error")

        # 执行下一个配置
        self.current_batch_index += 1
        self.execute_next_config_in_batch(
            self.host_ip.currentText().strip(),
            self.username.text().strip(),
            self.password.text().strip(),
            self.get_selected_env(self.env_group)
        )

    def on_batch_execute_finished(self):
        """批量执行完成"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        total = len(self.batch_configs)
        success = self.batch_success_count
        failed = self.batch_failed_count

        message = f"批量执行完成！\n成功: {success} 个\n失败: {failed} 个\n总计: {total} 个"

        if failed == 0:
            QMessageBox.information(self, "批量执行完成", message)
        else:
            QMessageBox.warning(self, "批量执行完成", message)

    def on_execute_finished(self, success: bool, message: str):
        """单个配置执行完成处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, "执行成功", message)
        else:
            QMessageBox.warning(self, "执行失败", message)

    def log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.parent_window:
            self.parent_window.append_log(message, level)

    def on_restart_pos_linux(self):
        """重启Linux POS"""
        from pos_tool_new.linux_pos.linux_service import LinuxService
        service = LinuxService()
        host = self.host_ip.currentText().strip()
        username = self.username.text().strip() or "menu"
        password = self.password.text().strip() or "M2ei#a$19!"
        reply = QMessageBox.warning(
            self,
            "确认重启",
            "该过程可能耗时1-4分钟，确定重启吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            ssh = service._connect_ssh(host, username, password)
            ssh.close()
        except Exception as e:
            if hasattr(self, 'parent_window') and self.parent_window:
                self.parent_window.append_log("SSH连接失败，无法重启POS", "error")
            return
        self.restart_btn.setEnabled(False)
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("POS重启中：%p%，请勿进行其他操作！")
            self.parent_window.setup_progress_animation(600)
        from pos_tool_new.work_threads import RestartPosThreadLinux
        self.restart_thread = RestartPosThreadLinux(service, host, username, password)
        self.restart_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
        self.restart_thread.finished_updated.connect(self.on_restart_finished)
        self.restart_thread.start()

    def on_restart_finished(self):
        if hasattr(self, 'parent_window') and self.parent_window:
            self.parent_window.on_restart_finished()
        self.restart_btn.setEnabled(True)
    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()

    def reload_config(self):
        """重新加载配置文件并刷新所有tab"""
        self.service._load_config()
        self.refresh_config_list()

    def closeEvent(self, event):
        if hasattr(self, 'modify_thread') and self.modify_thread.isRunning():
            self.modify_thread.quit()
            self.modify_thread.wait()
        super().closeEvent(event)

    def set_host_ip(self, ip: str):
        """同步设置主机IP到host_ip输入框"""
        if self.host_ip:
            self.host_ip.setCurrentText(ip)
