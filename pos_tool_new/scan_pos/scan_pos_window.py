from pos_tool_new.main import BaseTabWidget
from .scan_pos_service import ScanPosService
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout,
                             QLabel, QProgressBar, QLineEdit, QHBoxLayout,
                             QHeaderView, QSizePolicy, QSpacerItem, QWidget)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QBrush, QDesktopServices


class ScanPosTabWidget(BaseTabWidget):
    def __init__(self, backend, parent=None):
        super().__init__('扫描POS', parent)
        self.backend = backend
        self.service = ScanPosService()
        self._results = []
        self._total_scan_count = 0  # 总扫描IP数量
        self._scanned_count = 0  # 已扫描IP数量
        self._loaded_count = 0  # 已加载到表格的数量
        self._scan_finished = False  # 扫描是否完成
        self._displayed_results = []  # 当前显示的结果

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
        self.progress_bar.setTextVisible(True)
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
        self.progress_bar.hide()  # 初始隐藏进度条

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

        # 控制按钮和搜索在同一行
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_btn)
        control_layout.addLayout(search_layout)

        # 进度布局单独一行
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addSpacing(10)
        progress_layout.addWidget(self.progress_label)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)  # 按钮和搜索在同一行
        main_layout.addSpacing(5)
        main_layout.addLayout(progress_layout)  # 进度条单独一行
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
        self._displayed_results = []
        self._total_scan_count = 0
        self._scanned_count = 0
        self._loaded_count = 0
        self._scan_finished = False

        # 显示进度条
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.progress_label.setText('扫描初始化...')

        worker = self.service.start_scan()
        if worker is None:
            self.progress_label.setText('扫描进行中...')
            return

        worker.scan_progress.connect(self.on_scan_progress)
        worker.scan_result.connect(self.on_scan_result)
        worker.scan_finished.connect(self.on_scan_finished)
        worker.scan_total.connect(self.on_scan_total)
        worker.start()

    def on_scan_total(self, total_count):
        """处理总扫描数量"""
        self._total_scan_count = total_count
        self.progress_label.setText(f'开始扫描，共 {total_count} 个IP')

    def on_scan_progress(self, percent, ip):
        """处理扫描进度更新"""
        # 扫描阶段更新进度条
        if not self._scan_finished:
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f'正在扫描: {ip} ({percent}%)')

    def on_scan_result(self, result):
        """处理单个扫描结果 - 只收集数据，不实时添加到表格"""
        self._results.append(result)
        self._scanned_count += 1

        # 扫描阶段：显示扫描进度
        if not self._scan_finished and self._total_scan_count > 0:
            scan_percent = int((self._scanned_count / self._total_scan_count) * 100)
            self.progress_bar.setValue(scan_percent)
            self.progress_label.setText(
                f'扫描进度: {self._scanned_count}/{self._total_scan_count} ({scan_percent}%) - 发现设备: {len(self._results)}')

    def on_scan_finished(self, results):
        """处理扫描完成"""
        self._scan_finished = True
        self._results = results
        self._loaded_count = 0  # 加载阶段从0开始
        # 无条件进入加载阶段
        self.progress_label.setText(f'扫描完成，开始加载数据到表格...')
        self.progress_bar.setValue(0)  # 加载阶段进度条重置为0
        self._start_loading_phase()

    def _start_loading_phase(self):
        """开始加载阶段"""
        from PyQt6.QtCore import QTimer
        self._load_timer = QTimer()
        self._load_timer.timeout.connect(self._load_next_row)
        self._load_timer.start(50)  # 每50毫秒加载一行

    def _load_next_row(self):
        """加载下一行数据"""
        if self._loaded_count >= len(self._results):
            # 加载完成
            self._load_timer.stop()
            self.progress_bar.setValue(100)
            self.progress_label.setText(f'加载完成，共 {len(self._results)} 台设备')

            # 延迟隐藏进度条
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, self.hide_progress_bar)
            return

        # 加载当前行
        result = self._results[self._loaded_count]
        self._add_row_to_table(result, self._loaded_count)
        self._loaded_count += 1

        # 更新加载进度
        if len(self._results) > 0:
            load_percent = int((self._loaded_count / len(self._results)) * 100)
            self.progress_bar.setValue(load_percent)
            self.progress_label.setText(f'加载进度: {self._loaded_count}/{len(self._results)} ({load_percent}%)')

    def _add_row_to_table(self, result, row_index):
        """向表格添加单行数据"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 设置交替行背景色
        bg_color = self.row_colors[row_index % 2]

        # IP地址
        ip_item = QTableWidgetItem(result.get('ip', ''))
        ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        ip_item.setBackground(QBrush(bg_color))
        self.table.setItem(row, 0, ip_item)

        # 商家ID
        merchant_item = QTableWidgetItem(str(result.get('merchantId', '')))
        merchant_item.setFlags(merchant_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        merchant_item.setBackground(QBrush(bg_color))
        self.table.setItem(row, 1, merchant_item)

        # 商家名称
        name_item = QTableWidgetItem(str(result.get('name', '')))
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        name_item.setBackground(QBrush(bg_color))
        self.table.setItem(row, 2, name_item)

        # 版本或错误信息
        if result.get('status') == 'success':
            version_item = QTableWidgetItem(str(result.get('version', '')))
        else:
            version_item = QTableWidgetItem(str(result.get('error', '获取失败')))
            version_item.setForeground(Qt.GlobalColor.red)

        version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        version_item.setBackground(QBrush(bg_color))
        self.table.setItem(row, 3, version_item)

        # 操作按钮
        ip = result.get('ip', '')
        btn = QPushButton('打开')
        btn.setStyleSheet(
            'QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 4px; padding: 4px 8px; } QPushButton:hover { background-color: #0b7dda; }')
        btn.clicked.connect(lambda _, ip=ip: QDesktopServices.openUrl(QUrl(f'http://{ip}:22080')))
        self.table.setCellWidget(row, 4, btn)

        # 自动滚动到最后一行
        self.table.scrollToBottom()

    def hide_progress_bar(self):
        """隐藏进度条"""
        self.progress_bar.hide()

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
        """刷新表格数据（用于搜索）"""
        self.table.setRowCount(0)
        self._displayed_results = results

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