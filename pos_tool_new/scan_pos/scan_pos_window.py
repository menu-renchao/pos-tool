from pos_tool_new.main import BaseTabWidget
from .scan_pos_service import ScanPosService
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout,
                             QLabel, QProgressBar, QLineEdit, QHBoxLayout, QHeaderView, QWidget)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QColor, QBrush, QDesktopServices


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
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['IP', '商家ID', '名称', '版本', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)

        self.refresh_btn = QPushButton('扫描/刷新')
        self.refresh_btn.clicked.connect(self.start_scan)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)  # 显示百分比文本
        self.progress_bar.hide()

        self.progress_label = QLabel('准备扫描...')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.search_id_edit, self.search_name_edit = QLineEdit(), QLineEdit()
        self.search_id_edit.setPlaceholderText('输入商家ID')
        self.search_name_edit.setPlaceholderText('输入商家名称')
        self.search_btn = QPushButton('搜索')
        self.search_btn.clicked.connect(self.on_search)
        self.clear_search_btn = QPushButton('清除')
        self.clear_search_btn.clicked.connect(self.clear_search)

        self._setup_layouts()

    def _setup_layouts(self):
        search_layout = QHBoxLayout()
        for label, widget in [('商家ID:', self.search_id_edit), ('商家名称:', self.search_name_edit)]:
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

    def on_scan_progress(self, percent, ip):
        if not self._scan_finished:
            # 更新进度条值
            self.progress_bar.setValue(int(percent))
            self.progress_label.setText(f'正在扫描: {ip} ({percent}%)')

    def on_scan_result(self, result):
        self._results.append(result)
        self._scanned_count += 1
        self._loaded_count += 1
        self._add_row_to_table(result, self._loaded_count - 1)

        # 计算加载进度
        if len(self._results) > 0:
            load_percent = min(100, int((self._loaded_count / len(self._results)) * 100))
            self.progress_bar.setValue(load_percent)

        self.progress_label.setText(f'正在加载第 {self._loaded_count} 条...')

    def on_scan_finished(self, results):
        self._scan_finished = True
        self._results = results
        # 设置进度条为100%
        self.progress_bar.setValue(100)
        self.progress_label.setText(f'加载完成，共 {len(self._results)} 台设备')
        QTimer.singleShot(2000, self.progress_bar.hide)

    def _add_row_to_table(self, result, row_index):
        self.table.insertRow(self.table.rowCount())
        bg_color = self.row_colors[row_index % 2]
        for col, key in enumerate(['ip', 'merchantId', 'name', 'version']):
            item = QTableWidgetItem(str(result.get(key, '')))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QBrush(bg_color))
            self.table.setItem(row_index, col, item)
        btn = QPushButton('打开')
        btn.setFixedWidth(48)
        btn.setFixedHeight(22)
        btn.setStyleSheet(
            'QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 3px; padding: 2px 8px; font-size: 11px; } '
            'QPushButton:hover { background-color: #0b7dda; }'
        )
        btn.clicked.connect(lambda _, ip=result.get('ip', ''): QDesktopServices.openUrl(QUrl(f'http://{ip}:22080')))
        # 居中显示按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.addWidget(btn)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row_index, 4, btn_widget)
        self.table.scrollToBottom()

    def on_search(self):
        id_text, name_text = self.search_id_edit.text().strip().lower(), self.search_name_edit.text().strip().lower()
        self._refresh_table([r for r in self._results if
                             id_text in str(r.get('merchantId', '')).lower() and name_text in str(
                                 r.get('name', '')).lower()])

    def clear_search(self):
        self.search_id_edit.clear()
        self.search_name_edit.clear()
        self._refresh_table(self._results)

    def _refresh_table(self, results):
        self.table.setRowCount(0)
        for i, result in enumerate(results):
            self._add_row_to_table(result, i)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()