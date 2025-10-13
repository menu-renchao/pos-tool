from pos_tool_new.main import BaseTabWidget
from .scan_pos_service import ScanPosService
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout,
                             QLabel, QProgressBar, QLineEdit, QHBoxLayout,
                             QHeaderView, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QBrush, QDesktopServices


class ScanPosTabWidget(BaseTabWidget):
    def __init__(self, backend, parent=None):
        super().__init__('扫描POS', parent)
        self.backend = backend
        self.service = ScanPosService()
        self._results = []

        # 定义条纹颜色
        self.row_colors = [
            QColor(255, 255, 255),  # 白色
            QColor(240, 240, 240)  # 浅灰色
        ]

        self._init_ui()

    def _init_ui(self):
        """初始化所有UI组件"""
        # 创建表格，5列，最后一列为操作
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['IP', '商家ID', '名称', '版本', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 设置表格样式
        self.table.setAlternatingRowColors(True)  # 启用交替行颜色
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f8f8f8;
                padding: 5px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
            }
        """)

        # 扫描按钮
        self.refresh_btn = QPushButton('扫描/刷新')
        self.refresh_btn.setFixedWidth(150)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.refresh_btn.clicked.connect(self.start_scan)

        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
        """)

        self.progress_label = QLabel('准备扫描...')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 搜索组件
        self.search_id_edit = QLineEdit()
        self.search_id_edit.setPlaceholderText('输入商家ID')
        self.search_id_edit.setClearButtonEnabled(True)
        self.search_id_edit.setFixedWidth(200)

        self.search_name_edit = QLineEdit()
        self.search_name_edit.setPlaceholderText('输入商家名称')
        self.search_name_edit.setClearButtonEnabled(True)
        self.search_name_edit.setFixedWidth(200)

        self.search_btn = QPushButton('搜索')
        self.search_btn.setFixedWidth(80)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.search_btn.clicked.connect(self.on_search)

        self.clear_search_btn = QPushButton('清除')
        self.clear_search_btn.setFixedWidth(80)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)

        # 创建布局
        self._setup_layouts()

    def _setup_layouts(self):
        """设置所有布局"""
        # 搜索栏布局
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('商家ID:'))
        search_layout.addWidget(self.search_id_edit)
        search_layout.addSpacing(10)
        search_layout.addWidget(QLabel('商家名称:'))
        search_layout.addWidget(self.search_name_edit)
        search_layout.addSpacing(10)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)
        search_layout.addStretch()

        # 控制按钮布局
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_btn)
        control_layout.addStretch()

        # 进度布局
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addSpacing(10)
        progress_layout.addWidget(self.progress_label)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(search_layout)
        main_layout.addSpacing(10)
        main_layout.addLayout(control_layout)
        main_layout.addSpacing(5)
        main_layout.addLayout(progress_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.table)

        # 设置间距和边距
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)

        self.layout.addLayout(main_layout)

    def start_scan(self):
        """开始扫描"""
        self.table.setRowCount(0)
        self._results = []
        self.progress_bar.setValue(0)
        self.progress_label.setText('扫描初始化...')

        worker = self.service.start_scan()
        if worker is None:
            self.progress_label.setText('扫描进行中...')
            return

        worker.scan_progress.connect(self.on_scan_progress)
        worker.scan_result.connect(self.on_scan_result)
        worker.scan_finished.connect(self.on_scan_finished)
        worker.start()

    def on_scan_progress(self, percent, ip):
        """处理扫描进度更新"""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f'正在扫描: {ip} ({percent}%)')

    def on_scan_result(self, result):
        """处理单个扫描结果"""
        self._results.append(result)
        self._refresh_table(self._results)

    def on_scan_finished(self, results):
        """处理扫描完成"""
        self.progress_bar.setValue(100)
        self.progress_label.setText(f'扫描完成，共发现 {len(results)} 台设备')
        self._refresh_table(results)

    def on_search(self):
        """执行搜索"""
        id_text = self.search_id_edit.text().strip().lower()
        name_text = self.search_name_edit.text().strip().lower()

        filtered = []
        for r in self._results:
            # 检查商家ID匹配
            if id_text and id_text not in str(r.get('merchantId', '')).lower():
                continue
            # 检查商家名称匹配
            if name_text and name_text not in str(r.get('name', '')).lower():
                continue
            filtered.append(r)

        self._refresh_table(filtered)

    def clear_search(self):
        """清除搜索条件"""
        self.search_id_edit.clear()
        self.search_name_edit.clear()
        self._refresh_table(self._results)

    def _refresh_table(self, results):
        """刷新表格数据"""
        self.table.setRowCount(0)

        for i, result in enumerate(results):
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 设置交替行背景色
            for col in range(self.table.columnCount()):
                item = QTableWidgetItem()
                item.setBackground(QBrush(self.row_colors[i % 2]))
                self.table.setItem(row, col, item)

            # IP地址
            ip_item = QTableWidgetItem(result.get('ip', ''))
            ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            ip_item.setBackground(QBrush(self.row_colors[i % 2]))
            self.table.setItem(row, 0, ip_item)

            # 商家ID
            merchant_item = QTableWidgetItem(str(result.get('merchantId', '')))
            merchant_item.setFlags(merchant_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            merchant_item.setBackground(QBrush(self.row_colors[i % 2]))
            self.table.setItem(row, 1, merchant_item)

            # 商家名称
            name_item = QTableWidgetItem(str(result.get('name', '')))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setBackground(QBrush(self.row_colors[i % 2]))
            self.table.setItem(row, 2, name_item)

            # 版本或错误信息
            if result.get('status') == 'success':
                version_item = QTableWidgetItem(str(result.get('version', '')))
            else:
                version_item = QTableWidgetItem(str(result.get('error', '获取失败')))
                version_item.setForeground(Qt.GlobalColor.red)

            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            version_item.setBackground(QBrush(self.row_colors[i % 2]))
            self.table.setItem(row, 3, version_item)

            # 操作按钮
            ip = result.get('ip', '')
            btn = QPushButton('打开')
            btn.setStyleSheet('QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #0b7dda; }')
            btn.clicked.connect(lambda _, ip=ip: QDesktopServices.openUrl(QUrl(f'http://{ip}:22080')))
            self.table.setCellWidget(row, 4, btn)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()