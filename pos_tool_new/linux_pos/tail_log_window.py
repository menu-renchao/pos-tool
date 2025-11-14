from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QTimer
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QTimer
from PyQt6.QtGui import QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QLineEdit, QCheckBox,
                             QPushButton, QLabel, QTextEdit, QSizePolicy)
from PyQt6.QtWidgets import (QProgressBar)

from pos_tool_new.work_threads import RemoteTailLogThread


class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor("#fff3cd"))  # 浅黄色背景
        self.highlight_format.setForeground(QColor("#856404"))  # 深棕色文字
        self.pattern = ""
        self.case_sensitive = False

    def set_pattern(self, pattern, case_sensitive=False):
        self.pattern = pattern
        self.case_sensitive = case_sensitive
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.pattern:
            return

        # 创建正则表达式
        flags = QRegularExpression.PatternOption.NoPatternOption
        if not self.case_sensitive:
            flags = QRegularExpression.PatternOption.CaseInsensitiveOption

        regex = QRegularExpression(self.pattern, flags)
        if not regex.isValid():
            return

        # 查找所有匹配
        iterator = regex.globalMatch(text)
        while iterator.hasNext():
            match = iterator.next()
            start = match.capturedStart()
            length = match.capturedLength()
            self.setFormat(start, length, self.highlight_format)


class FindDialog(QDialog):
    find_next = pyqtSignal(str, bool, bool)  # text, case_sensitive, highlight_all
    find_previous = pyqtSignal(str, bool, bool)  # text, case_sensitive, highlight_all
    highlight_all = pyqtSignal(str, bool)  # text, case_sensitive

    def __init__(self, text_edit: QTextEdit = None, parent=None):
        super().__init__(parent)
        assert text_edit is not None, "text_edit must be provided to FindDialog!"
        self.text_edit = text_edit
        self.highlighter = None
        self.current_matches = []
        self.current_match_index = -1
        self.find_timer = QTimer()
        self.find_timer.setSingleShot(True)
        self.find_timer.setInterval(300)  # 300ms延迟搜索

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("查找日志内容")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(450, 180)
        self.setStyleSheet(self.get_stylesheet())

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(12)
        input_layout.setContentsMargins(0, 12, 0, 8)

        input_label = QLabel("查找:")
        input_label.setFixedWidth(40)

        self.input = QLineEdit()
        self.input.setPlaceholderText("输入要查找的关键词...")
        self.input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)

        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input, 1)

        main_layout.addLayout(input_layout)

        # 选项区域
        options_layout = QHBoxLayout()
        options_layout.setSpacing(16)

        self.case_cb = QCheckBox("区分大小写")
        self.regex_cb = QCheckBox("正则表达式")
        self.regex_cb.setStyleSheet(self.case_cb.styleSheet())

        self.highlight_cb = QCheckBox("高亮所有匹配项")
        self.highlight_cb.setStyleSheet(self.case_cb.styleSheet())
        self.highlight_cb.setChecked(True)
        self.highlight_cb.toggled.connect(self.on_highlight_toggled)

        options_layout.addWidget(self.case_cb)
        options_layout.addWidget(self.regex_cb)
        options_layout.addWidget(self.highlight_cb)
        options_layout.addStretch()

        main_layout.addLayout(options_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)
        button_layout.setContentsMargins(0, 12, 0, 0)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setMaximumWidth(160)  # 限制最大宽度，可根据实际调整
        self.status_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #95a5a6;
                font-style: italic;
            }
        """)

        button_layout.addWidget(self.status_label)
        button_layout.addStretch()

        self.prev_btn = QPushButton("上一个")
        self.prev_btn.setEnabled(False)

        self.next_btn = QPushButton("下一个")
        self.next_btn.setEnabled(False)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.close_btn)

        main_layout.addLayout(button_layout)

    def setup_connections(self):
        """设置信号连接"""
        self.input.textChanged.connect(self.on_text_changed)
        self.prev_btn.clicked.connect(self.find_previous_clicked)
        self.next_btn.clicked.connect(self.find_next_clicked)
        self.highlight_cb.toggled.connect(self.on_highlight_toggled)
        self.case_cb.toggled.connect(self.on_options_changed)  # 新增
        self.regex_cb.toggled.connect(self.on_options_changed)  # 新增
        self.find_timer.timeout.connect(self.delayed_search)

        # 回车键查找下一个
        self.input.returnPressed.connect(self.find_next_clicked)

    def on_options_changed(self, checked):
        """选项变化处理（区分大小写、正则表达式）"""
        if self.input.text().strip() and self.highlight_cb.isChecked():
            # 如果有搜索文本且高亮开启，立即刷新高亮
            self.highlight_all_clicked()

    def get_stylesheet(self):
        """返回样式表"""
        return """
            QDialog {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """

    def on_text_changed(self, text):
        """文本变化处理 - 使用延迟搜索避免频繁操作"""
        has_text = len(text.strip()) > 0
        self.prev_btn.setEnabled(has_text)
        self.next_btn.setEnabled(has_text)

        if not has_text:
            self.status_label.setText("就绪")
            self.clear_highlight()
            self.find_timer.stop()
        else:
            # 停止之前的计时器，重新开始延迟搜索
            self.find_timer.stop()
            self.find_timer.start()

    def delayed_search(self):
        """延迟搜索，避免频繁操作导致卡顿"""
        if self.highlight_cb.isChecked():
            self.highlight_all_clicked()

    def on_highlight_toggled(self, checked):
        """高亮复选框状态变化"""
        if not checked:
            self.clear_highlight()
        elif self.input.text().strip():
            self.highlight_all_clicked()

    def highlight_all_clicked(self):
        """高亮所有匹配项 - 优化性能"""
        if not hasattr(self, 'text_edit') or self.text_edit is None:
            return

        text = self.input.text().strip()
        if not text:
            return

        # 清除旧的高亮
        self.clear_highlight()

        # 创建高亮器
        if not self.highlighter:
            self.highlighter = LogHighlighter(self.text_edit.document())

        # 设置高亮模式
        pattern = text
        if not self.regex_cb.isChecked():
            pattern = QRegularExpression.escape(pattern)

        case_sensitive = self.case_cb.isChecked()
        self.highlighter.set_pattern(pattern, case_sensitive)

        # 异步统计匹配数量（避免大文档卡顿）
        QTimer.singleShot(0, self.count_matches_async)

    def count_matches_async(self):
        """异步统计匹配数量"""
        try:
            document = self.text_edit.document()
            text = document.toPlainText()
            search_text = self.input.text().strip()

            if not search_text:
                return

            # 使用简单的字符串计数（比QTextCursor查找更快）
            if self.case_cb.isChecked():
                match_count = text.count(search_text)
            else:
                match_count = text.lower().count(search_text.lower())

            if match_count > 0:
                self.status_label.setText(f"发现{match_count} 个")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            else:
                self.status_label.setText("未找到")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

        except Exception as e:
            self.status_label.setText("统计错误")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def clear_highlight(self):
        """清除高亮"""
        if self.highlighter:
            self.highlighter.set_pattern("")
            self.highlighter = None
        self.current_matches = []
        self.current_match_index = -1
        self.status_label.setText("就绪")
        self.status_label.setStyleSheet("color: #95a5a6; font-style: italic;")

    def find_next_clicked(self):
        """查找下一个"""
        self.perform_find(forward=True)

    def find_previous_clicked(self):
        """查找上一个"""
        self.perform_find(forward=False)

    def perform_find(self, forward=True):
        """执行查找操作 - 优化性能"""
        text = self.input.text().strip()
        if not text or not self.text_edit:
            return

        # 设置查找选项
        options = QTextDocument.FindFlag(0)
        if self.case_cb.isChecked():
            options |= QTextDocument.FindFlag.FindCaseSensitively

        # 获取当前光标位置
        cursor = self.text_edit.textCursor()

        # 如果光标没有选择文本，移动到单词开始
        if not cursor.hasSelection():
            if forward:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfWord)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.EndOfWord)

        # 执行查找
        if forward:
            found = self.text_edit.find(text, options)
        else:
            found = self.text_edit.find(text, options | QTextDocument.FindFlag.FindBackward)

        if found:
            self.status_label.setText("匹配项已找到")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            # 确保匹配项在视图中可见
            self.text_edit.ensureCursorVisible()
        else:
            # 没找到，尝试从开始/结束位置重新查找
            cursor = QTextCursor(self.text_edit.document())
            if forward:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.text_edit.setTextCursor(cursor)
                found = self.text_edit.find(text, options)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.text_edit.setTextCursor(cursor)
                found = self.text_edit.find(text, options | QTextDocument.FindFlag.FindBackward)

            if found:
                self.status_label.setText("已循环查找")
                self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                self.text_edit.ensureCursorVisible()
            else:
                self.status_label.setText("未找到匹配项")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        QTimer.singleShot(100, self.set_input_focus)

    def set_input_focus(self):
        """设置输入框焦点"""
        self.input.selectAll()
        self.input.setFocus()

    def closeEvent(self, event):
        """关闭事件"""
        self.find_timer.stop()
        self.clear_highlight()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class TailLogWindow(QDialog):
    # 添加自定义信号用于外部控制
    window_closed = pyqtSignal()

    def __init__(self, file_path, ssh_params=None, remote=False, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.ssh_params = ssh_params
        self.remote = remote
        self.is_tailing = True
        self.user_scrolled = False  # 标志：用户是否手动滚动

        self.setup_ui()
        self.setup_thread()

        # 查找相关
        self.find_dialog = None

    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle(f"实时日志 - {self.file_path.split('/')[-1]}")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1400, 700)
        self.setMinimumSize(800, 400)

        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton#stopBtn {
                background-color: #da3633;
            }
            QPushButton#stopBtn:hover {
                background-color: #b32623;
            }
            QPushButton#pauseBtn {
                background-color: #d67f00;
            }
            QPushButton#pauseBtn:hover {
                background-color: #b36200;
            }
            QLabel {
                color: #333333;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                background-color: white;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
        """)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # 标题栏
        title_layout = QHBoxLayout()

        self.title_label = QLabel(f"实时日志监控: {self.file_path}")
        self.title_label.setStyleSheet("font-size: 14px; color: #333;")

        self.status_label = QLabel("● 连接中...")
        self.status_label.setStyleSheet("color: #d67f00; font-weight: bold;")

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.status_label)

        # 信息栏
        info_layout = QHBoxLayout()

        self.file_info_label = QLabel(f"文件: {self.file_path}")
        self.file_info_label.setStyleSheet("color: #666; font-size: 11px;")

        self.connection_info_label = QLabel("远程连接" if self.remote else "本地文件")
        self.connection_info_label.setStyleSheet("color: #007acc; font-size: 11px;")

        info_layout.addWidget(self.file_info_label)
        info_layout.addStretch()
        info_layout.addWidget(self.connection_info_label)

        # 日志显示区域
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)  # 不自动换行

        # 添加行号功能
        font = QFont("Consolas", 10)
        self.text_edit.setFont(font)

        # 连接滚动条事件
        self.text_edit.verticalScrollBar().valueChanged.connect(self.on_scrollbar_changed)

        # 控制按钮区域
        control_layout = QHBoxLayout()

        # 左侧功能按钮
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self.clear_log)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.clicked.connect(self.toggle_pause)

        self.wrap_btn = QPushButton("切换换行")
        self.wrap_btn.clicked.connect(self.toggle_wrap)

        # 查找按钮
        self.find_btn = QPushButton("查找")
        self.find_btn.clicked.connect(self.show_find_dialog)

        # 右侧操作按钮
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_tailing)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        control_layout.addWidget(self.clear_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.wrap_btn)
        control_layout.addWidget(self.find_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.close_btn)

        # 进度指示器
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 无限进度条

        # 统计信息栏
        stats_layout = QHBoxLayout()

        self.line_count_label = QLabel("行数: 0")
        self.line_count_label.setStyleSheet("color: #666; font-size: 11px;")

        self.update_time_label = QLabel("最后更新: --")
        self.update_time_label.setStyleSheet("color: #666; font-size: 11px;")

        stats_layout.addWidget(self.line_count_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.update_time_label)

        # 添加到主布局
        main_layout.addLayout(title_layout)
        main_layout.addLayout(info_layout)
        main_layout.addWidget(self.text_edit, 1)  # 设置伸缩因子为1
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(control_layout)
        main_layout.addLayout(stats_layout)

        # 初始化状态
        self.line_count = 0
        self.is_paused = False
        self.wrap_enabled = False

    def setup_thread(self):

        if self.remote and self.ssh_params:
            service, host, username, password = self.ssh_params[:4]
            self.thread = RemoteTailLogThread(service, host, username, password, self.file_path)
        else:
            # 这里可以添加本地文件监控的逻辑
            self.thread = None

        if self.thread:
            self.thread.log_updated.connect(self.append_log)
            self.thread.connection_status.connect(self.update_connection_status)
            self.thread.start()
            self.progress_bar.setVisible(True)

    def append_log(self, text):
        """追加日志内容"""
        if self.is_paused:
            return

        # 处理换行和统计
        lines = text.split('\n')
        valid_lines = [line for line in lines if line.strip()]
        self.line_count += len(valid_lines)

        # 添加时间戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 批量添加文本，减少UI更新次数
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        for line in valid_lines:
            formatted_text = f"[{timestamp}] {line}\n"
            cursor.insertText(formatted_text)

        # 更新统计信息
        self.update_stats()

        # 自动滚动到底部（如果不是暂停状态且用户未手动滚动）
        if not self.is_paused and not self.user_scrolled:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.ensureCursorVisible()

    def on_scrollbar_changed(self, value):
        scrollbar = self.text_edit.verticalScrollBar()
        # 判断是否在底部
        if value < scrollbar.maximum():
            self.user_scrolled = True
        else:
            self.user_scrolled = False

    def update_connection_status(self, status, message):
        """更新连接状态"""
        status_colors = {
            "connected": "#107c10",
            "error": "#da3633",
            "connecting": "#d67f00"
        }
        color = status_colors.get(status, "#666666")
        self.status_label.setText(f"● {message}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        if status == "connected":
            self.progress_bar.setVisible(False)

    def update_stats(self):
        """更新统计信息"""
        self.line_count_label.setText(f"行数: {self.line_count}")
        from datetime import datetime
        self.update_time_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")

    def clear_log(self):
        """清空日志"""
        self.text_edit.clear()
        self.line_count = 0
        self.update_stats()

    def toggle_pause(self):
        """切换暂停/继续状态"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("继续")
            self.status_label.setText("● 已暂停")
            self.status_label.setStyleSheet("color: #666; font-weight: bold;")
        else:
            self.pause_btn.setText("暂停")
            self.status_label.setText("● 监控中")
            self.status_label.setStyleSheet("color: #107c10; font-weight: bold;")

    def toggle_wrap(self):
        """切换换行模式"""
        self.wrap_enabled = not self.wrap_enabled
        if self.wrap_enabled:
            self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            self.wrap_btn.setText("取消换行")
        else:
            self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            self.wrap_btn.setText("切换换行")

    def stop_tailing(self):
        """停止监控"""
        self.is_tailing = False
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("停止中...")

        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.status_label.setText("● 停止中...")
            self.status_label.setStyleSheet("color: #666; font-weight: bold;")

    def show_find_dialog(self):
        """显示查找对话框"""
        if self.find_dialog is None:
            self.find_dialog = FindDialog(self.text_edit, self)

        self.find_dialog.show()
        self.find_dialog.activateWindow()
        self.find_dialog.raise_()

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.stop_tailing()

        # 关闭查找对话框
        if self.find_dialog:
            self.find_dialog.close()

        if self.thread and self.thread.isRunning():
            self.thread.wait(2000)  # 等待2秒

        self.window_closed.emit()
        event.accept()

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.show_find_dialog()
        else:
            super().keyPressEvent(event)
