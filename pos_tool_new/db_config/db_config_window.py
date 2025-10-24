from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, \
    QFormLayout, QMessageBox, QDialog, QLineEdit, QTextEdit, QCheckBox, QDialogButtonBox, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QWidget, QHeaderView, QSizePolicy

from pos_tool_new.main import BaseTabWidget, MainWindow
from pos_tool_new.work_threads import DatabaseConnectThread, RestartPosThreadLinux
from .db_config_service import DbConfigService, ConfigItem
from ..linux_pos.linux_service import LinuxService


class SqlDetailDialog(QDialog):
    """SQL详情弹窗"""

    def __init__(self, sql_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle('SQL详情')
        self.setMinimumSize(800, 300)
        layout = QVBoxLayout(self)

        # SQL内容显示
        self.sql_edit = QTextEdit()
        self.sql_edit.setPlainText(sql_text)
        self.sql_edit.setReadOnly(True)
        self.sql_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 8px;
                font-family: monospace;
            }
        """)
        layout.addWidget(QLabel('SQL语句:'))
        layout.addWidget(self.sql_edit)

        # 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)


class ConfigEditDialog(QDialog):
    def __init__(self, service, item=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.item = item
        self.setWindowTitle('编辑配置项' if item else '新增配置项')
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        layout = QFormLayout(self)

        # 描述编辑框
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("请输入功能描述...")

        # SQL编辑框
        self.sqls_edit = QTextEdit()
        self.sqls_edit.setPlaceholderText("请输入SQL语句，每条SQL占一行...")
        self.sqls_edit.setMinimumHeight(200)

        # 重启复选框
        self.restart_check = QCheckBox('需要重启生效')
        self.restart_check.setToolTip("勾选后表示此配置需要重启数据库才能生效")

        # 填充数据（编辑模式）
        if item:
            self.desc_edit.setText(item.description)
            self.sqls_edit.setPlainText('\n'.join(item.sqls))
            self.restart_check.setChecked(item.need_restart)

        # 添加表单行
        layout.addRow('功能描述:', self.desc_edit)
        layout.addRow('SQL语句组:', self.sqls_edit)
        layout.addRow('', self.restart_check)

        # 按钮框
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def accept(self):
        desc = self.desc_edit.text().strip()
        sqls = [s.strip() for s in self.sqls_edit.toPlainText().split('\n') if s.strip()]
        if not desc:
            QMessageBox.warning(self, '错误', '功能描述不能为空')
            return
        if not sqls:
            QMessageBox.warning(self, '错误', '至少需要输入一条SQL语句')
            return
        # 唯一性校验（编辑时排除自身）
        items = self.service.get_config_items()
        if self.item:
            if any(i.description.lower() == desc.lower() and i.description != self.item.description for i in items):
                QMessageBox.warning(self, '错误', '功能描述必须唯一，请重新输入')
                return
        else:
            if any(i.description.lower() == desc.lower() for i in items):
                QMessageBox.warning(self, '错误', '功能描述必须唯一，请重新输入')
                return
        super().accept()

    def get_data(self):
        desc = self.desc_edit.text().strip()
        sqls = [s.strip() for s in self.sqls_edit.toPlainText().split('\n') if s.strip()]
        need_restart = self.restart_check.isChecked()
        return ConfigItem(desc, sqls, need_restart)



class DbConfigWindow(BaseTabWidget):
    """
    数据库配置项 UI，包含筛选框、单选框、执行按钮。
    """

    def __init__(self, parent=None):
        super().__init__(title="数据库配置", parent=parent)
        self.service = DbConfigService()
        self.parent_window :MainWindow= parent
        self.init_ui()

    def init_ui(self):
        # 主布局 - 使用更紧凑的间距
        main_layout = self.layout
        main_layout.setSpacing(6)  # 减少间距
        main_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距

        # 数据库连接组 - 紧凑样式
        db_group = QGroupBox("连接配置")
        db_group.setStyleSheet("""
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
        db_layout = QFormLayout()
        db_layout.setContentsMargins(0, 0, 0, 0)  # 减少内边距
        db_layout.setSpacing(4)  # 减少间距
        db_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.host_combo = QComboBox()
        self.host_combo.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        self.host_combo.setEditable(True)
        self.host_combo.setMinimumWidth(180)  # 稍微减小宽度
        self.host_combo.setStyleSheet("QComboBox { padding: 3px; font-size: 11px; }")  # 紧凑样式
        self.host_combo.setToolTip("选择或输入数据库主机地址")

        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: gray; font-weight: normal; font-size: 11px;")

        self.connect_btn = QPushButton("连接")
        self.connect_btn.setFixedWidth(70)  # 减小宽度
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BBDEFB;
            }
        """)
        self.connect_btn.clicked.connect(self.connect_database)

        # Add Restart POS button next to connect_btn
        self.restart_btn = QPushButton("重启pos（仅作用于linux）")
        self.restart_btn.setToolTip("重启POS服务，可能耗时1-4分钟")
        self.restart_btn.setFixedWidth(180)  # 减小宽度
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

        db_row_layout = QHBoxLayout()
        db_row_layout.setContentsMargins(0, 0, 0, 0)
        db_row_layout.setSpacing(6)  # 减少间距
        db_row_layout.addWidget(QLabel("主机地址:"))
        db_row_layout.addWidget(self.host_combo)
        db_row_layout.addWidget(QLabel("状态:"))
        db_row_layout.addWidget(self.status_label)
        db_row_layout.addWidget(self.connect_btn)
        db_row_layout.addWidget(self.restart_btn)
        db_row_layout.addStretch()
        db_layout.addRow(db_row_layout)

        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)

        # 配置管理区 - 紧凑样式
        config_group = QGroupBox("配置规则管理")
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

        # 搜索框 - 紧凑布局
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        search_label = QLabel("搜索规则:")
        search_label.setStyleSheet("font-size: 11px;")
        search_layout.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('输入关键字搜索规则描述或SQL内容...')
        self.search_edit.setStyleSheet("QLineEdit { padding: 3px; font-size: 11px; }")
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit)
        config_layout.addLayout(search_layout)

        # 操作按钮区域 - 紧凑样式
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        self.btn_add = QPushButton('新增规则')
        self.btn_exec = QPushButton('批量执行选中规则')
        self.btn_reload_config = QPushButton('重载配置文件')

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
        self.btn_add.setStyleSheet(button_style + """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-color: #45a049;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_exec.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-color: #1976D2;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_reload_config.setStyleSheet(button_style + """
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-color: #F57C00;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        self.btn_add.clicked.connect(self.on_add_config)
        self.btn_exec.clicked.connect(self.on_exec_config)
        self.btn_reload_config.clicked.connect(self.refresh_config_table)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_exec)
        btn_layout.addWidget(self.btn_reload_config)
        btn_layout.addStretch()
        config_layout.addLayout(btn_layout)

        # 表格 - 紧凑样式
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(5)
        self.config_table.setAlternatingRowColors(True)
        self.config_table.setHorizontalHeaderLabels(['选择', '描述', 'SQL预览(点击展开)', '重启要求', '操作'])

        # 紧凑表格样式
        self.config_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: white;
                selection-background-color: transparent;
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
        """)

        # 设置表格选择行为
        self.config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.config_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        # 设置表格尺寸策略
        self.config_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 设置列宽比例 - 更紧凑的列宽
        header = self.config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # 设置固定列宽 - 减小宽度
        self.config_table.setColumnWidth(0, 50)  # 选择列
        self.config_table.setColumnWidth(3, 80)  # 重启要求列
        self.config_table.setColumnWidth(4, 140)  # 操作列

        self.config_table.verticalHeader().setVisible(False)
        self.config_table.cellClicked.connect(self.on_table_cell_clicked)

        # 关键修改：将表格添加到布局并设置拉伸因子
        config_layout.addWidget(self.config_table, 1)  # 拉伸因子为1

        # 关键修改：将配置组添加到主布局并设置拉伸因子
        main_layout.addWidget(config_group, 1)  # 拉伸因子为1

        # 初始化表格数据
        self.refresh_config_table()

    def on_table_cell_clicked(self, row, column):
        """处理表格单元格点击事件"""
        if column == 2:  # SQL预览列
            item = self.service.get_config_items()[row]
            sql_text = '\n'.join(item.sqls)
            dlg = SqlDetailDialog(sql_text, self)
            dlg.exec()
        elif column == 0:  # 复选框列，不处理特殊事件，让复选框正常工作
            pass

    def get_selected_configs(self):
        """获取选中的配置项（通过复选框）"""
        selected_items = []
        for row in range(self.config_table.rowCount()):
            checkbox = self.config_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                item = self.service.get_config_items()[row]
                selected_items.append(item.description)
        return selected_items

    def get_selected_config_items(self):
        selected_items = []
        # 按表格行顺序和勾选状态返回原始ConfigItem对象
        for row in range(self.config_table.rowCount()):
            checkbox = self.config_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_items.append(self._current_table_items[row])
        return selected_items

    def on_search_changed(self, text):
        self.refresh_config_table(text)

    def refresh_config_table(self, keyword=''):
        """刷新配置表格"""
        self.config_table.setRowCount(0)
        try:
            items = self.service.get_config_items()
        except Exception as e:
            self.service.log(f"获取配置项失败: {e}","error")
            return
        # 搜索过滤
        if keyword:
            keyword = keyword.strip().lower()
            items = [item for item in items if
                     keyword in item.description.lower() or
                     any(keyword in sql.lower() for sql in item.sqls) or
                     (keyword in '是需重启' and item.need_restart) or
                     (keyword in '否无需' and not item.need_restart)]
        self._current_table_items = items  # 保存当前表格显示的原始ConfigItem列表

        # 填充表格数据
        for row, item in enumerate(items):
            self.config_table.insertRow(row)

            # 复选框列
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin-left: 5px; }")
            self.config_table.setCellWidget(row, 0, checkbox)

            # 描述列
            desc_item = QTableWidgetItem(item.description)
            desc_item.setToolTip(item.description)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.config_table.setItem(row, 1, desc_item)

            # SQL预览列
            sql_preview = item.sqls[0] if item.sqls else "无SQL语句"
            sql_item = QTableWidgetItem(sql_preview)
            sql_item.setToolTip("点击查看完整SQL详情")
            sql_item.setFlags(sql_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.config_table.setItem(row, 2, sql_item)

            # 重启要求列
            restart_text = '是，需重启' if item.need_restart else '否，立即生效'
            restart_item = QTableWidgetItem(restart_text)
            restart_item.setToolTip("配置生效方式")
            restart_item.setFlags(restart_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            if item.need_restart:
                restart_item.setForeground(Qt.GlobalColor.red)
            else:
                restart_item.setForeground(Qt.GlobalColor.darkGreen)
            self.config_table.setItem(row, 3, restart_item)

            # 操作列 - 紧凑按钮
            op_widget = QWidget()
            op_layout = QHBoxLayout(op_widget)
            op_layout.setContentsMargins(2, 1, 2, 1)  # 减少内边距
            op_layout.setSpacing(4)  # 减少间距

            btn_edit = QPushButton('编辑')
            btn_delete = QPushButton('删除')
            btn_run = QPushButton('执行')

            # 设置按钮大小和样式
            for btn in [btn_edit, btn_delete, btn_run]:
                btn.setFixedSize(45, 24)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 9px;
                        padding: 2px 4px;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                    }
                """)

            # 特殊样式
            btn_edit.setStyleSheet("QPushButton { background-color: #FFC107; color: black; font-size: 10px; }")
            btn_delete.setStyleSheet("QPushButton { background-color: #F44336; color: white; font-size: 10px; }")
            btn_run.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 10px; }")

            # 连接信号
            btn_edit.clicked.connect(lambda checked, r=row: self.on_edit_config(r))
            btn_delete.clicked.connect(lambda checked, r=row: self.on_delete_config(r))
            btn_run.clicked.connect(lambda checked, r=row: self.on_run_config(r))

            op_layout.addWidget(btn_edit)
            op_layout.addWidget(btn_delete)
            op_layout.addWidget(btn_run)
            op_layout.addStretch()

            self.config_table.setCellWidget(row, 4, op_widget)

            # 设置更小的行高
            self.config_table.setRowHeight(row, 30)  # 减小行高

    def on_add_config(self):
        dlg = ConfigEditDialog(self.service, parent=self)
        if dlg.exec():
            new_item = dlg.get_data()
            if not new_item.description:
                QMessageBox.warning(self, '错误', '功能描述不能为空')
                return
            if not new_item.sqls:
                QMessageBox.warning(self, '错误', '至少需要输入一条SQL语句')
                return
            # 检查描述是否唯一
            if any(i.description.lower() == new_item.description.lower()
                   for i in self.service.get_config_items()):
                QMessageBox.warning(self, '错误', '功能描述必须唯一，请重新输入')
                return

            self.service.add_config_item(new_item)
            self.refresh_config_table()
            QMessageBox.information(self, '成功', '配置项添加成功')

    def on_edit_config(self, row):
        """编辑配置项"""
        original_item = self.service.get_config_items()[row]
        dlg = ConfigEditDialog(self.service, original_item, parent=self)
        if dlg.exec():
            new_item = dlg.get_data()

            # 验证数据
            if not new_item.description:
                QMessageBox.warning(self, '错误', '功能描述不能为空')
                return
            if not new_item.sqls:
                QMessageBox.warning(self, '错误', '至少需要输入一条SQL语句')
                return

            # 检查描述是否唯一（排除自身）
            if any(i.description.lower() == new_item.description.lower()
                   and i.description != original_item.description
                   for i in self.service.get_config_items()):
                QMessageBox.warning(self, '错误', '功能描述必须唯一，请重新输入')
                return

            self.service.update_config_item(new_item, original_item.description)
            self.refresh_config_table()
            QMessageBox.information(self, '成功', '配置项更新成功')

    def on_delete_config(self, row):
        """删除配置项"""
        item = self.service.get_config_items()[row]
        reply = QMessageBox.question(self, '确认删除',
                                     f'确定要删除配置项 "{item.description}" 吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.service.delete_config_item(item.description)
            self.refresh_config_table()
            QMessageBox.information(self, '成功', '配置项删除成功')

    def on_exec_config(self):
        """批量执行选中的配置项"""
        selected_items = self.get_selected_config_items()
        if not selected_items:
            QMessageBox.warning(self, '提示', '请先通过复选框选择要执行的规则')
            return

        reply = QMessageBox.question(self, '确认执行',
                                     f'确定要执行选中的 {len(selected_items)} 个配置规则吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        db_params = self.get_db_params()
        try:
            result = self.service.set_config(selected_items, db_params)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'执行配置项时发生错误: {str(e)}')
            return

        # 格式化执行结果
        success_count = sum(1 for v in result.values() if not v)  # 无需重启的视为立即成功
        restart_count = sum(1 for v in result.values() if v)  # 需要重启的

        msg = f"执行完成！\n\n立即生效: {success_count} 个\n需要重启: {restart_count} 个\n\n"
        msg += "\n".join([f"{k}: {'需重启' if v else '立即生效'}" for k, v in result.items()])

        msg_box = QMessageBox(QMessageBox.Icon.Information, '执行结果', msg, parent=self)
        msg_box.setMinimumSize(400, 200)
        msg_box.exec()

    def on_run_config(self, row):
        """执行单个配置项"""
        item = self._current_table_items[row]  # 用当前表格显示的数据
        reply = QMessageBox.question(self, '确认执行',
                                     f'确定要执行配置项 "{item.description}" 吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        db_params = self.get_db_params()
        try:
            result = self.service.set_config([item], db_params)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'执行配置项时发生错误: {str(e)}')
            return
        msg = f"{item.description}: {'需重启生效' if result.get(item.description) else '立即生效'}"
        msg_box = QMessageBox(QMessageBox.Icon.Information, '执行结果', msg, parent=self)
        msg_box.setMinimumSize(400, 200)
        msg_box.exec()
    def on_worker_error(self, msg):
        self.log_message(msg, "error")

    def on_worker_result(self, success, msg):
        if success:
            self.log_message(msg, "success")
        else:
            self.log_message(msg, "error")

    def on_worker_finished(self):
        self.worker = None

    def get_db_params(self):
        return {
            'host': self.host_combo.currentText(),
            'port': 22108,
            'user': 'shohoku',
            'password': 'N0mur@4$99!',
            'database': 'kpos'
        }

    def log_message(self, message: str, level: str = "info"):
        """使用后端方法记录日志"""
        self.service.log(message, level)

    def on_connect_success(self, success, message):
        if success:
            self.status_label.setText(f"{message}")
            self.status_label.setStyleSheet("color: green; font-weight: normal;")
            self.log_message(message, "success")
        else:
            self.status_label.setText("连接失败")
            self.status_label.setStyleSheet("color: red; font-weight: normal;")
            self.log_message(f"连接失败: {message}", "error")
            QMessageBox.warning(self, "连接失败", message)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接")

    def on_connect_error(self, error_message):
        self.log_message(f"连接异常: {error_message}", "error")
        QMessageBox.critical(self, "错误", f"连接异常: {error_message}")

    def connect_database(self):
        """连接数据库"""
        host = self.host_combo.currentText().strip()
        if not host:
            QMessageBox.warning(self, "警告", "请输入主机地址")
            return

        self.log_message(f"正在连接数据库: {host}", "info")
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")

        self.db_thread = DatabaseConnectThread(self.service, host)
        self.db_thread.finished_updated.connect(self.on_connect_success)
        self.db_thread.error_occurred.connect(self.on_connect_error)
        self.db_thread.start()


    def on_restart_pos_linux(self):
        """重启Linux POS"""
        service = LinuxService()
        def restart_pos_callback(host, username, password):
            # 显示确认弹窗
            reply = QMessageBox.warning(
                self,
                "确认重启",
                "该过程可能耗时1-4分钟，确定重启吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # 先尝试连接SSH
            try:
                ssh = service._connect_ssh(self.host_combo.currentText().strip(),'menu',"M2ei#a$19!")
                ssh.close()
            except Exception as e:
                self.log_message("SSH连接失败，无法重启POS", level="error")
                return

            # 禁用重启按钮
            self.restart_btn.setEnabled(False)

            # 显示进度条
            if self.parent_window:
                self.parent_window.progress_bar.setVisible(True)
                self.parent_window.progress_bar.setRange(0, 100)
                self.parent_window.progress_bar.setValue(0)
                self.parent_window.progress_bar.setFormat("POS重启中：%p%，请勿进行其他操作！")
            self.restart_thread = RestartPosThreadLinux(LinuxService(), host, username, password)

            # 设置进度条动画更新
            if self.parent_window:
                self.parent_window.setup_progress_animation(600)

            # 在线程完成后更新状态
            self.restart_thread.error_occurred.connect(lambda msg: QMessageBox.warning(self, "错误", msg))
            self.restart_thread.finished_updated.connect(self.on_restart_finished)
            self.restart_thread.start()

        restart_pos_callback(self.host_combo.currentText().strip(),'menu',"M2ei#a$19!")


    def on_restart_finished(self):
        """重启完成后处理"""
        if self.parent_window:
            self.parent_window.on_restart_finished()

        if self.restart_btn:
            self.restart_btn.setEnabled(True)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()

