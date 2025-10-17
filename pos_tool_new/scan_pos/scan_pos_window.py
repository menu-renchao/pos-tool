from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QColor, QBrush, QDesktopServices
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout,
                             QLabel, QProgressBar, QLineEdit, QHBoxLayout, QHeaderView, QWidget)

from pos_tool_new.main import BaseTabWidget
from .scan_pos_service import ScanPosService


class ScanPosTabWidget(BaseTabWidget):
    def __init__(self, backend, parent=None):
        super().__init__('扫描POS', parent)
        self.backend = backend
        self.service = ScanPosService()
        self._results, self._displayed_results = [], []
        self._total_scan_count = self._scanned_count = self._loaded_count = 0
        self._scan_finished = False
        self.row_colors = [QColor(255, 255, 255), QColor(240, 240, 240)]
        self._init_ui()

    def _init_ui(self):
        self._create_ui()
        self._bind_signals()
        self._setup_layouts()

    def _create_ui(self):
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['IP', '设备类型', '商家ID', '名称', '版本', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(False)  # 关闭自动隔行色

        self.refresh_btn = QPushButton('扫描/刷新')
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)  # 显示百分比文本
        self.progress_bar.hide()

        self.progress_label = QLabel('准备扫描...')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.search_id_edit, self.search_name_edit, self.search_ip_edit = QLineEdit(), QLineEdit(), QLineEdit()
        self.search_version_edit = QLineEdit()  # 新增版本筛选输入框
        self.search_id_edit.setPlaceholderText('输入商家ID')
        self.search_name_edit.setPlaceholderText('输入商家名称')
        self.search_ip_edit.setPlaceholderText('输入IP')
        self.search_version_edit.setPlaceholderText('输入版本')  # 新增
        self.search_btn = QPushButton('搜索')
        self.clear_search_btn = QPushButton('清除')

    def _bind_signals(self):
        self.refresh_btn.clicked.connect(self.start_scan)
        self.search_btn.clicked.connect(self.on_search)
        self.clear_search_btn.clicked.connect(self.clear_search)
        # 支持回车触发搜索
        self.search_id_edit.returnPressed.connect(self.on_search)
        self.search_name_edit.returnPressed.connect(self.on_search)
        self.search_ip_edit.returnPressed.connect(self.on_search)
        self.search_version_edit.returnPressed.connect(self.on_search)  # 新增

        self.table.horizontalHeader().sectionClicked.connect(self.on_section_clicked)

    def _setup_layouts(self):
        search_layout = QHBoxLayout()
        for label, widget in [('IP:', self.search_ip_edit), ('商家ID:', self.search_id_edit),
                              ('商家名称:', self.search_name_edit), ('版本:', self.search_version_edit)]:
            search_layout.addWidget(QLabel(label))
            search_layout.addWidget(widget)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_btn)
        control_layout.addLayout(search_layout)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addLayout(progress_layout)
        main_layout.addWidget(self.table)
        self.layout.addLayout(main_layout)

    def start_scan(self):
        self.refresh_btn.setEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self._results, self._displayed_results = [], []
        self._total_scan_count = self._scanned_count = self._loaded_count = 0
        self._scan_finished = False

        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText('扫描初始化...')

        worker = self.service.start_scan()
        if worker:
            worker.scan_progress.connect(self.on_scan_progress)
            worker.scan_result.connect(self.on_scan_result)
            worker.scan_finished.connect(self.on_scan_finished)
            worker.start()
        self.update_row_colors()

    def on_scan_progress(self, percent, ip):
        if not self._scan_finished:
            # 更新进度条值
            self.progress_bar.setValue(int(percent))
            self.progress_label.setText(f'正在扫描: {ip} ({percent}%)')

    def on_scan_result(self, result):
        self._results.append(result)
        self._scanned_count += 1
        self._loaded_count += 1
        self._add_row_to_table(result)
        if len(self._results) > 0:
            load_percent = min(100, int((self._loaded_count / len(self._results)) * 100))
            self.progress_bar.setValue(load_percent)
        self.progress_label.setText(f'正在加载第 {self._loaded_count} 条...')
        self.update_row_colors()

    def on_scan_finished(self, results):
        self._scan_finished = True
        self._results = results
        # 设置进度条为100%
        self.progress_bar.setValue(100)
        self.progress_label.setText(f'加载完成，共 {len(self._results)} 台设备')
        QTimer.singleShot(2000, self.progress_bar.hide)
        self.refresh_btn.setEnabled(True)  # 扫描结束后恢复按钮可用
        self.table.setSortingEnabled(True)

    def _add_row_to_table(self, result):
        self.table.insertRow(self.table.rowCount())
        row = self.table.rowCount() - 1
        bg_color = self.row_colors[row % 2]
        self._set_table_row_items(row, result, bg_color)
        if all(self.table.item(row, i).text() == '——' for i in [2, 3, 4]):
            unavailable_label = QLabel('POS已离线')
            unavailable_label.setStyleSheet('color: red; font-weight: bold;')
            unavailable_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 5, unavailable_label)
        else:
            self._create_row_buttons(row, result)
        self.table.scrollToBottom()
        self.update_row_colors()

    def _set_table_row_items(self, row, result, bg_color):
        def get_value(key):
            return result.get(key, '')
        for col, key in enumerate(['ip', 'type', 'merchantId', 'name', 'version']):
            value = get_value(key)
            if key == 'merchantId':
                name_val = get_value('name')
                version_val = get_value('version')
                if not value and name_val and version_val:
                    value = 'Free Trials'
            if not value:
                value = '——'
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QBrush(bg_color))
            self.table.setItem(row, col, item)

    def _create_row_buttons(self, row, result):
        def get_value(key):
            return result.get(key, '')
        btn_open = QPushButton('打开')
        btn_open.setFixedWidth(48)
        btn_open.setFixedHeight(22)
        btn_open.setStyleSheet(
            'QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 3px; padding: 2px 8px; font-size: 11px; } '
            'QPushButton:hover { background-color: #0b7dda; }'
        )
        btn_open.clicked.connect(lambda _, ip=get_value('ip'): QDesktopServices.openUrl(QUrl(f'http://{ip}:22080')))

        btn_detail = QPushButton('详情')
        btn_detail.setFixedWidth(48)
        btn_detail.setFixedHeight(22)
        btn_detail.setStyleSheet(
            'QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 3px; padding: 2px 8px; font-size: 11px; } '
            'QPushButton:hover { background-color: #357a38; }'
        )
        btn_detail.clicked.connect(lambda _, btn=btn_detail: self.show_detail_dialog_by_widget(btn))

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_detail)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 5, btn_widget)

    def show_detail_dialog_by_widget(self, widget):
        # 获取按钮所在的行号
        index = self.table.indexAt(widget.parent().pos())
        row = index.row()
        if row < 0:
            return
        ip = self.table.item(row, 0).text()
        # 在self._results中查找对应ip的数据
        for result in self._results:
            if str(result.get('ip', '')) == ip:
                self.show_detail_dialog_by_result(result)
                return

    def show_detail_dialog_by_result(self, result):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QHBoxLayout
        ip = result.get('ip', '')
        full_data = self.service.fetch_company_profile(ip)
        detail_data = self._filter_none_and_exclude(full_data)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"详情 - {ip}")
        if self.parent() and hasattr(self.parent(), 'size'):
            main_size = self.parent().size()
            dialog.resize(main_size)
        else:
            dialog.resize(self.size())
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        if detail_data and (not isinstance(detail_data, dict) or detail_data):
            self._add_kv_widgets_to_layout(detail_data, content_layout)
        else:
            content_layout.addWidget(QLabel("无数据"))
        scroll.setWidget(content)
        layout.addWidget(scroll)
        dialog.setLayout(layout)
        dialog.exec()

    def _filter_none_and_exclude(self, data):
        exclude_keys = {"appInstance", "images", "result", "printLogo"}
        if isinstance(data, dict):
            return {k: self._filter_none_and_exclude(v) for k, v in data.items() if v is not None and k not in exclude_keys}
        elif isinstance(data, list):
            return [self._filter_none_and_exclude(item) for item in data if item is not None]
        else:
            return data

    def _add_kv_widgets_to_layout(self, data, layout, indent=0):
        indent_px = indent * 20
        from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget
        if isinstance(data, dict):
            for k, v in data.items():
                key_label = QLabel(f"<b>{k}</b>")
                key_label.setStyleSheet(f"margin-left: {indent_px}px;")
                key_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                key_label.setMinimumWidth(180)
                key_label.setWordWrap(True)
                if isinstance(v, (dict, list)):
                    layout.addWidget(key_label)
                    self._add_kv_widgets_to_layout(v, layout, indent + 1)
                else:
                    row = QHBoxLayout()
                    row.setContentsMargins(0, 0, 0, 0)
                    row.setSpacing(8)
                    value_label = QLabel(str(v))
                    value_label.setWordWrap(True)
                    value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    row.addWidget(key_label)
                    row.addWidget(value_label)
                    row.addStretch()
                    row_widget = QWidget()
                    row_widget.setLayout(row)
                    row_widget.setStyleSheet(f"margin-left: {indent_px}px;")
                    layout.addWidget(row_widget)
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                key_label = QLabel(f"[{idx}]")
                key_label.setStyleSheet(f"margin-left: {indent_px}px;color:#888;")
                key_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                layout.addWidget(key_label)
                self._add_kv_widgets_to_layout(item, layout, indent + 1)
        else:
            value_label = QLabel(str(data))
            value_label.setStyleSheet(f"margin-left: {indent_px}px;")
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(value_label)

    def on_search(self):
        ip_text = self.search_ip_edit.text().strip().lower()
        id_text = self.search_id_edit.text().strip().lower()
        name_text = self.search_name_edit.text().strip().lower()
        version_text = self.search_version_edit.text().strip().lower()  # 新增

        def get_field(r, key):
            return str(r.get(key, '')).lower()

        filtered = [r for r in self._results if
                    ip_text in get_field(r, 'ip') and id_text in get_field(r, 'merchantId') and name_text in get_field(
                        r, 'name') and version_text in get_field(r, 'version')]
        self._refresh_table(filtered)

    def clear_search(self):
        self.search_ip_edit.clear()
        self.search_id_edit.clear()
        self.search_name_edit.clear()
        self.search_version_edit.clear()  # 新增
        self._refresh_table(self._results)

    def _refresh_table(self, results):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for result in results:
            self._add_row_to_table(result)
        self.table.setSortingEnabled(True)
        self.update_row_colors()

    def update_row_colors(self):
        # 按当前显示顺序重新分配隔行色
        for row in range(self.table.rowCount()):
            bg_color = self.row_colors[row % 2]
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QBrush(bg_color))

    def on_section_clicked(self, _):
        # 排序后刷新隔行色
        QTimer.singleShot(0, self.update_row_colors)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()
