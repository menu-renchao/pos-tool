import socket
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout,
                             QLabel, QProgressBar, QLineEdit, QHBoxLayout, QHeaderView, QWidget, QInputDialog, QMessageBox)
from pos_tool_new.main import BaseTabWidget
from .scan_printer_service import ScanPrinterService

class ScanPrinterTabWidget(BaseTabWidget):
    def __init__(self, backend, parent=None):
        super().__init__('扫描打印机/刷卡机', parent)
        self.backend = backend
        self.local_ip = None
        self.service = None
        self._results = []
        self.row_colors = [QColor(255, 255, 255), QColor(240, 240, 240)]
        self._init_ui()

    def _select_local_ip(self):
        ips = set()
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if "." in ip and not ip.startswith("127."):
                ips.add(ip)
        ips = list(ips)
        if len(ips) == 1:
            return ips[0]
        ip, ok = QInputDialog.getItem(self, "选择IP网段", "检测到本机多个IP网段，请选择:", ips, 0, False)
        if ok and ip:
            return ip
        return None

    def _init_ui(self):
        self._create_ui()
        self._bind_signals()
        self._setup_layouts()

    def _create_ui(self):
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['IP', '设备类型', '开放端口', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(False)
        self.refresh_btn = QPushButton('扫描/刷新')
        self.refresh_btn.setFixedWidth(120)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.progress_label = QLabel('准备扫描...')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _bind_signals(self):
        self.refresh_btn.clicked.connect(self.start_scan)
        self.table.horizontalHeader().sectionClicked.connect(self.on_section_clicked)

    def _setup_layouts(self):
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_btn)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addLayout(progress_layout)
        main_layout.addWidget(self.table)
        self.layout.addLayout(main_layout)

    def start_scan(self):
        self.local_ip = self._select_local_ip()
        if not self.local_ip:
            return
        self.service = ScanPrinterService(local_ip=self.local_ip)
        self.refresh_btn.setEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self._results = []
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText('扫描初始化...')
        worker = self.service.start_scan()
        if worker:
            worker.scan_progress.connect(self.on_scan_progress)
            worker.scan_finished.connect(self.on_scan_finished)
            worker.start()
        self.update_row_colors()

    def on_scan_progress(self, percent, ip):
        self.progress_bar.setValue(int(percent))
        self.progress_label.setText(f'正在扫描: {ip} ({percent}%)')

    def on_scan_finished(self, results):
        self._results = results
        self.progress_bar.setValue(100)
        self.progress_label.setText(f'加载完成，共 {len(self._results)} 台设备')
        QTimer.singleShot(2000, self.progress_bar.hide)
        self.refresh_btn.setEnabled(True)
        self.table.setSortingEnabled(True)
        self._refresh_table(results)
        self.update_row_colors()

    def _add_row_to_table(self, result):
        self.table.insertRow(self.table.rowCount())
        row = self.table.rowCount() - 1
        bg_color = self.row_colors[row % 2]
        ip_item = QTableWidgetItem(str(result.get('ip', '')))
        ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        ip_item.setBackground(QBrush(bg_color))
        type_item = QTableWidgetItem(str(result.get('type', '')))
        type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        type_item.setBackground(QBrush(bg_color))
        ports_item = QTableWidgetItem(','.join(str(p) for p in result.get('open_ports', [])))
        ports_item.setFlags(ports_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        ports_item.setBackground(QBrush(bg_color))
        self.table.setItem(row, 0, ip_item)
        self.table.setItem(row, 1, type_item)
        self.table.setItem(row, 2, ports_item)
        # 操作列
        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(0, 0, 0, 0)
        op_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        has_button = False
        if result.get('type', '') == '打印机':
            btn_print = QPushButton('测试打印')
            btn_print.setFixedWidth(80)
            btn_print.clicked.connect(lambda _, ip=result['ip']: self.on_test_print(ip))
            op_layout.addWidget(btn_print)
            has_button = True
        # 如果没有任何按钮，则显示占位符
        if not has_button:
            op_layout.addWidget(QLabel('——'))
        self.table.setCellWidget(row, 3, op_widget)

    def on_test_print(self, ip):
        self.service.test_print(ip)
        QMessageBox.information(self, '测试打印', f'已向 {ip}:9100 发送测试打印指令。')

    def _refresh_table(self, results):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for result in results:
            self._add_row_to_table(result)
        self.table.setSortingEnabled(True)
        self.update_row_colors()

    def update_row_colors(self):
        for row in range(self.table.rowCount()):
            bg_color = self.row_colors[row % 2]
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QBrush(bg_color))

    def on_section_clicked(self, _):
        QTimer.singleShot(0, self.update_row_colors)

    def showEvent(self, event):
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.show_main_log_area()
