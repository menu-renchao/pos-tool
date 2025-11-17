import copy
import os
from typing import Optional, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView,
    QDialog, QDialogButtonBox, QGroupBox, QRadioButton, QButtonGroup, QComboBox, QMessageBox,
    QWidget, QFileDialog, QInputDialog, QAbstractItemView, QSizePolicy
)

from pos_tool_new.main import BaseTabWidget, MainWindow
from pos_tool_new.windows_file_config.file_config_win_service import FileConfigItem, KeyValueItem, \
    WindowsFileConfigService
from pos_tool_new.work_threads import WindowsFileModifyThread


class KeyValueEditDialog(QDialog):
    def __init__(self, key_value_item: Optional[KeyValueItem] = None, parent=None):
        super().__init__(parent)
        self.key_value_item = key_value_item or KeyValueItem(key="")
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle("编辑键值对配置")
        self.setMinimumWidth(900)
        layout = QVBoxLayout(self)
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("键名:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("请输入配置键名，如：api.url")
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)
        env_layout = QVBoxLayout()
        qa_layout = QHBoxLayout()
        qa_layout.addWidget(QLabel("    QA:"))
        self.qa_edit = QLineEdit()
        self.qa_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        qa_layout.addWidget(self.qa_edit)
        env_layout.addLayout(qa_layout)
        prod_layout = QHBoxLayout()
        prod_layout.addWidget(QLabel("PROD:"))
        self.prod_edit = QLineEdit()
        self.prod_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        prod_layout.addWidget(self.prod_edit)
        env_layout.addLayout(prod_layout)
        dev_layout = QHBoxLayout()
        dev_layout.addWidget(QLabel("  DEV:"))
        self.dev_edit = QLineEdit()
        self.dev_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        dev_layout.addWidget(self.dev_edit)
        env_layout.addLayout(dev_layout)
        layout.addLayout(env_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_data(self):
        self.key_edit.setText(self.key_value_item.key)
        self.qa_edit.setText(self.key_value_item.qa_value)
        self.prod_edit.setText(self.key_value_item.prod_value)
        self.dev_edit.setText(self.key_value_item.dev_value)

    def get_key_value_item(self) -> KeyValueItem:
        item = copy.deepcopy(self.key_value_item)
        item.key = self.key_edit.text().strip()
        item.qa_value = self.qa_edit.text().strip()
        item.prod_value = self.prod_edit.text().strip()
        item.dev_value = self.dev_edit.text().strip()
        return item


class FileConfigEditDialog(QDialog):
    """文件配置编辑对话框（Windows版）"""

    def __init__(self, config_item: Optional[FileConfigItem] = None, parent=None):
        super().__init__(parent)
        self.config_item = copy.deepcopy(config_item) if config_item else FileConfigItem(name="", file_path="",
                                                                                         key_values=[])
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle("编辑文件配置")
        self.setMinimumWidth(900)
        layout = QVBoxLayout(self)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("配置名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入配置项名称")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("文件路径:"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("相对路径，如：kpos/front/js/cloudUrlConfig.json")
        path_layout.addWidget(self.path_edit)
        layout.addLayout(path_layout)
        layout.addWidget(QLabel("键值对配置:"))
        self.key_value_table = QTableWidget()
        self.key_value_table.setColumnCount(2)
        self.key_value_table.setHorizontalHeaderLabels(["键名", "值"])
        self.key_value_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.key_value_table.setColumnWidth(0, 120)
        self.key_value_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.key_value_table)
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
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.key_value_table.itemSelectionChanged.connect(self.on_selection_changed)

    def load_data(self):
        self.name_edit.setText(self.config_item.name)
        self.path_edit.setText(self.config_item.file_path)
        self.refresh_key_value_table()

    def refresh_key_value_table(self):
        self.key_value_table.setRowCount(0)
        for i, kv_item in enumerate(self.config_item.key_values):
            self.key_value_table.insertRow(i)
            self.key_value_table.setItem(i, 0, QTableWidgetItem(kv_item.key))
            value_text = f"QA: {kv_item.qa_value}\nPROD: {kv_item.prod_value}\nDEV: {kv_item.dev_value}"
            value_label = QLabel(value_text)
            value_label.setWordWrap(True)
            value_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.key_value_table.setCellWidget(i, 1, value_label)
            self.key_value_table.setRowHeight(i, 60)

    def on_selection_changed(self):
        has_selection = len(self.key_value_table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def add_key_value(self):
        dialog = KeyValueEditDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_item = dialog.get_key_value_item()
            if new_item.key:
                self.config_item.key_values.append(new_item)
                self.refresh_key_value_table()

    def edit_key_value(self):
        selected_rows = set(item.row() for item in self.key_value_table.selectedItems())
        if not selected_rows:
            return
        row = list(selected_rows)[0]
        if row < len(self.config_item.key_values):
            dialog = KeyValueEditDialog(self.config_item.key_values[row])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.config_item.key_values[row] = dialog.get_key_value_item()
                self.refresh_key_value_table()

    def delete_key_value(self):
        selected_rows = set(item.row() for item in self.key_value_table.selectedItems())
        if not selected_rows:
            return
        for row in sorted(selected_rows, reverse=True):
            if 0 <= row < len(self.config_item.key_values):
                del self.config_item.key_values[row]
        self.refresh_key_value_table()

    def get_config_item(self) -> FileConfigItem:
        return FileConfigItem(
            name=self.name_edit.text().strip(),
            file_path=self.path_edit.text().strip(),
            key_values=self.config_item.key_values.copy(),
            enabled=True
        )


class WindowsFileConfigTabWidget(BaseTabWidget):
    """Windows文件配置管理选项卡"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window: MainWindow = parent
        self.service = WindowsFileConfigService()
        self.setup_ui()
        self.refresh_config_list()

    def setup_ui(self):
        main_layout = self.layout
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)
        self._setup_path_selector()
        # 连接设置组
        connection_group = QGroupBox("连接设置")
        connection_layout = QVBoxLayout(connection_group)

        # 连接类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("连接类型:"))

        self.local_radio = QRadioButton("本地计算机")
        self.ssh_radio = QRadioButton("OpenSSH远程连接")
        self.local_radio.setChecked(True)

        self.connection_type_group = QButtonGroup(self)
        self.connection_type_group.addButton(self.local_radio)
        self.connection_type_group.addButton(self.ssh_radio)

        type_layout.addWidget(self.local_radio)
        type_layout.addWidget(self.ssh_radio)
        type_layout.addStretch()

        connection_layout.addLayout(type_layout)

        # SSH连接设置（默���隐藏）
        self.ssh_settings_layout = QHBoxLayout()

        # 主机IP
        host_label = QLabel("主机IP:")
        self.host_ip = QComboBox()
        self.host_ip.addItems(["192.168.0.", "192.168.1.", "10.0.0.", "localhost"])
        self.host_ip.setEditable(True)
        self.host_ip.setFixedWidth(120)

        # 环境选择
        env_frame, self.env_group = self.create_env_selector("QA")
        env_frame.setFixedWidth(200)

        # 用户名密码
        username_label = QLabel("用户名:")
        self.username = QLineEdit()
        self.username.setFixedWidth(100)

        password_label = QLabel("密码:")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedWidth(100)

        self.ssh_settings_layout.addWidget(host_label)
        self.ssh_settings_layout.addWidget(self.host_ip)
        self.ssh_settings_layout.addWidget(env_frame)
        self.ssh_settings_layout.addWidget(username_label)
        self.ssh_settings_layout.addWidget(self.username)
        self.ssh_settings_layout.addWidget(password_label)
        self.ssh_settings_layout.addWidget(self.password)
        self.ssh_settings_layout.addStretch()

        connection_layout.addLayout(self.ssh_settings_layout)

        # 连接类型切换事件
        self.local_radio.toggled.connect(self.on_connection_type_changed)
        self.on_connection_type_changed(True)  # 初始状态

        main_layout.addWidget(connection_group)

        # 配置列表组
        config_group = QGroupBox("文件配置列表")
        config_layout = QVBoxLayout(config_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("新增配置")
        self.execute_all_btn = QPushButton("执行所有启用配置")
        self.reload_btn = QPushButton("重载配置文件")

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

        # 配置表格
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(5)
        self.config_table.setAlternatingRowColors(True)
        self.config_table.setHorizontalHeaderLabels(['启用', '配置名称', '文件路径', '键值对数量', '操作'])
        # 设置表格选择行为
        self.config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.config_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # 设置表格尺寸策略
        self.config_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        header = self.config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.config_table.setColumnWidth(0, 50)
        self.config_table.setColumnWidth(3, 80)
        self.config_table.verticalHeader().setVisible(False)
        self.config_table.itemSelectionChanged.connect(self.on_selection_changed)

        config_layout.addWidget(self.config_table)
        main_layout.addWidget(config_group)

    def on_connection_type_changed(self, checked):
        """连接类型切换事件"""
        if self.local_radio.isChecked():
            # 本地模式，隐藏SSH设置
            for i in range(self.ssh_settings_layout.count()):
                item = self.ssh_settings_layout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(False)
            # 只显示环境选择
            self.ssh_settings_layout.itemAt(2).widget().setVisible(True)  # 环境选择
        else:
            # SSH模式，显示所有设置
            for i in range(self.ssh_settings_layout.count()):
                item = self.ssh_settings_layout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(True)

    def create_env_selector(self, default_env="QA"):
        """创建环境选择器"""
        env_frame = QWidget()
        env_layout = QHBoxLayout(env_frame)
        env_layout.setContentsMargins(0, 0, 0, 0)

        env_layout.addWidget(QLabel("环境:"))

        env_group = QButtonGroup(self)
        prod_radio = QRadioButton("PROD")
        qa_radio = QRadioButton("QA")
        dev_radio = QRadioButton("DEV")
        env_group.addButton(prod_radio)
        env_group.addButton(qa_radio)
        env_group.addButton(dev_radio)
        env_layout.addWidget(prod_radio)
        env_layout.addWidget(qa_radio)
        env_layout.addWidget(dev_radio)

        if default_env == "QA":
            qa_radio.setChecked(True)
        elif default_env == "PROD":
            prod_radio.setChecked(True)
        else:
            dev_radio.setChecked(True)

        return env_frame, env_group

    def _setup_path_selector(self):
        path_group = QGroupBox("基础目录")
        path_layout = QHBoxLayout(path_group)
        self.base_path = QLineEdit(r"C:\Wisdomount\Menusifu\application")
        self.base_path.setPlaceholderText("请选择基础目录...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.base_path)
        path_layout.addWidget(btn_browse)
        self.layout.addWidget(path_group)

    def get_selected_env(self, env_group) -> str:
        """获取选中的环境"""
        for button in env_group.buttons():
            if button.isChecked():
                return button.text()
        return "QA"

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
            self.config_table.setCellWidget(i, 0, checkbox)

            # 配置名称
            name_item = QTableWidgetItem(config.name)
            name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self.config_table.setItem(i, 1, name_item)

            # 文件路径
            path_item = QTableWidgetItem(config.file_path)
            path_item.setFlags(path_item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self.config_table.setItem(i, 2, path_item)

            # 键值对数量
            kv_btn = QPushButton(str(len(config.key_values)))
            kv_btn.clicked.connect(lambda checked, cfg=config: self.on_show_detail(cfg))
            kv_btn.setStyleSheet(
                'QPushButton { border: none; color: blue; text-decoration: underline; background: transparent; }')
            self.config_table.setCellWidget(i, 3, kv_btn)

            # 操作列
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 1, 2, 1)

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
            self.config_table.setRowHeight(i, 30)

    def on_selection_changed(self):
        """选择变化时更新按钮状态"""
        has_selection = len(self.config_table.selectionModel().selectedRows()) > 0
        # self.execute_btn.setEnabled(has_selection)

    def on_toggle_enabled(self, config: FileConfigItem, state: int):
        """切换配置启用状态"""
        enabled = (state == Qt.CheckState.Checked.value)
        self.service.toggle_config_enabled(config.name, enabled)

    def _get_versions(self):
        try:
            return [d for d in os.listdir(self.base_path.text()) if
                    os.path.isdir(os.path.join(self.base_path.text(), d))]
        except Exception as e:
            QMessageBox.warning(self, "提示", f"读取目录失败：{str(e)}")
            return []

    def select_version(self, versions):
        if not versions:
            return None
        if len(versions) == 1:
            return versions[0]
        selected_version, ok = QInputDialog.getItem(self, "选择版本", "请选择版本：", versions, 0, False)
        return selected_version if ok else None

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
        dialog.exec()

    def _validate_connection_params(self) -> tuple:
        """验证连接参数"""
        connection_type = "local" if self.local_radio.isChecked() else "ssh"
        env = self.get_selected_env(self.env_group)

        if connection_type == "ssh":
            host = self.host_ip.currentText().strip()
            username = self.username.text().strip()
            password = self.password.text().strip()

            if not host or host.endswith('.'):
                return False, "请填写完整的主机IP地址！", "", "", "", "", ""

            if not username:
                return False, "请填写用户名！", "", "", "", "", ""

            if not password:
                return False, "请填写密码！", "", "", "", "", ""

            return True, "", connection_type, host, username, password, env
        else:
            return True, "", connection_type, "", "", "", env

    def on_execute_single(self, config: FileConfigItem):
        """执行单个配置"""
        is_valid, error_msg, connection_type, host, username, password, env = self._validate_connection_params()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return

        if not config.enabled:
            QMessageBox.warning(self, "提示", "该配置项未启用，无法执行")
            return

        versions = self._get_versions()
        select_version = self.select_version(versions)
        if not select_version:
            return

        base_path = self.base_path.text()

        # 显示进度条
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat(f"正在执行配置: {config.name}")

        # 启动线程
        # 启动线程前，先安全销毁旧线程
        if hasattr(self, 'modify_thread') and self.modify_thread is not None and self.modify_thread.isRunning():
            self.modify_thread.stop()
        self.modify_thread = WindowsFileModifyThread(
            self.service, connection_type, host, username, password, config, env, select_version, base_path
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
        # 禁用批量执行按钮，防止高频点击
        self.execute_all_btn.setEnabled(False)
        # self.execute_btn.setEnabled(False)

        is_valid, error_msg, connection_type, host, username, password, env = self._validate_connection_params()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return

        versions = self._get_versions()
        select_version = self.select_version(versions)
        if not select_version:
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

        base_path = self.base_path.text()
        self.execute_configs_batch(enabled_configs, connection_type, host, username, password, env, select_version,
                                   base_path)

    def execute_configs_batch(self, configs: List[FileConfigItem], connection_type: str,
                              host: str, username: str, password: str, env: str, select_version: str, base_path: str):
        """批量执行配置"""
        if not configs:
            self.execute_all_btn.setEnabled(True)
            return
        self.batch_configs = configs.copy()
        self.current_batch_index = 0
        self.batch_success_count = 0
        self.batch_failed_count = 0
        # 保存批量参数为成员变量，供后续方法调用
        self.connection_type = connection_type
        self.host = host
        self.username = username
        self.password = password
        self.env = env
        self.selected_version = select_version
        self.base_path_value = base_path
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(True)
            self.parent_window.progress_bar.setRange(0, len(configs) * 100)
            self.parent_window.progress_bar.setValue(0)
            self.parent_window.progress_bar.setFormat("批量执行配置中...")
        self.execute_next_config_in_batch(connection_type, host, username, password, env, select_version, base_path)

    def execute_next_config_in_batch(self, connection_type: str, host: str, username: str, password: str, env: str,
                                     select_version: str, base_path: str):
        """执行批次的下一个配置"""
        if self.current_batch_index >= len(self.batch_configs):
            self.on_batch_execute_finished()
            return
        # 新建线程前，严格 stop+wait 旧线程
        if hasattr(self, 'modify_thread') and self.modify_thread is not None and self.modify_thread.isRunning():
            self.modify_thread.stop()
        self.modify_thread = WindowsFileModifyThread(
            self.service, connection_type, host, username, password, self.batch_configs[self.current_batch_index], env,
            select_version, base_path
        )

        self.modify_thread.progress_updated.connect(
            lambda percent: self.on_batch_progress_updated(self.current_batch_index, percent)
        )
        # 修正信号连接，避免 lambda 捕获问题
        self.modify_thread.finished_updated.connect(self.on_single_config_finished)
        self.modify_thread.start()

    def on_batch_progress_updated(self, config_index: int, percent: int):
        """批量执行进度更新"""
        if self.parent_window:
            base_progress = config_index * 100
            current_progress = base_progress + percent
            self.parent_window.progress_bar.setValue(current_progress)

    def on_single_config_finished(self, success: bool, message: str):
        """单个配置执行完成"""
        if success:
            self.batch_success_count += 1
        else:
            self.batch_failed_count += 1

        self.current_batch_index += 1
        self.execute_next_config_in_batch(
            self.connection_type, self.host, self.username, self.password, self.env, self.selected_version, self.base_path_value
        )

    def on_batch_execute_finished(self):
        """批量执行完成"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)
        # 批量执行完成后恢复按钮
        self.execute_all_btn.setEnabled(True)
        # self.execute_btn.setEnabled(True)

        total = len(self.batch_configs)
        success = self.batch_success_count
        failed = self.batch_failed_count

        message = f"批量执行完成！\n成功: {success} 个\n失败: {failed} 个\n总计: {total} 个"

        if failed == 0:
            QMessageBox.information(self, "批量执行完成", message)
        else:
            QMessageBox.warning(self, "批量执行完成", message)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择基础目录", self.base_path.text())
        if dir_path:
            self.base_path.setText(dir_path)

    def on_execute_finished(self, success: bool, message: str):
        """单个配置执行完成处理"""
        if self.parent_window:
            self.parent_window.progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, "执行成功", message)
        else:
            QMessageBox.warning(self, "执行失败", message)

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
        """窗口关闭时安全销毁线程"""
        if hasattr(self, 'modify_thread') and self.modify_thread is not None and self.modify_thread.isRunning():
            self.modify_thread.stop()
        event.accept()

    def set_host_ip(self, ip: str):
        """同步设置主机IP到host_ip输入框"""
        if self.host_ip:
            self.host_ip.setCurrentText(ip)