# random_mail_window.py
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
                             QListWidget, QTextEdit, QCheckBox, QListWidgetItem, QSplitter, QWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QSize
from pos_tool_new.main import BaseTabWidget
from .random_mail_service import RandomMailService
from pos_tool_new.work_threads import RandomMailLoadThread, RandomMailContentThread, ReusableMailContentThread
from PyQt6.QtGui import QMovie


class MailListItemWidget(QWidget):
    def __init__(self, subject, sender, time_str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # 主题
        lbl_subject = QLabel(subject)
        lbl_subject.setWordWrap(False)
        lbl_subject.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lbl_subject.setMinimumWidth(180)
        lbl_subject.setMaximumHeight(22)
        lbl_subject.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl_subject)

        # 发件人
        lbl_sender = QLabel(sender)
        lbl_sender.setWordWrap(False)
        lbl_sender.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lbl_sender.setMinimumWidth(120)
        lbl_sender.setMaximumHeight(18)
        lbl_sender.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl_sender)

        # 时间
        lbl_time = QLabel(time_str)
        lbl_time.setWordWrap(False)
        lbl_time.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lbl_time.setMinimumWidth(100)
        lbl_time.setMaximumHeight(16)
        lbl_time.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl_time)
        layout.addStretch()





class RandomMailTabWidget(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__("随机邮箱", parent)
        self.service = RandomMailService()
        self.init_ui()
        self.setup_connections()
        self.refresh_mails()
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_mails)
        self.toggle_auto_refresh(False)
        self.init_loading_overlay()  # 初始化加载蒙层
        self.content_thread = ReusableMailContentThread(self.service)
        self.content_thread.mail_content_loaded.connect(self.on_mail_content_loaded)
        self.content_thread.error_occurred.connect(self.on_mail_content_error)
        self._last_mail_id = None

    def init_loading_overlay(self):
        """初始化加载中蒙层"""
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setStyleSheet("background: rgba(255,255,255,180);")
        self.loading_overlay.setVisible(False)
        self.loading_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.raise_()

        layout = QVBoxLayout(self.loading_overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 可替换为自定义gif路径
        try:
            self.loading_movie = QMovie("../UI/loading.gif")
            if self.loading_movie.isValid():
                self.loading_label.setMovie(self.loading_movie)
                self.loading_movie.start()
            else:
                self.loading_label.setText("加载中...")
        except Exception:
            self.loading_label.setText("加载中...")
        layout.addWidget(self.loading_label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(self.rect())

    def show_loading_overlay(self):
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.setVisible(True)
        self.loading_overlay.raise_()
        if hasattr(self, 'loading_movie') and self.loading_movie:
            self.loading_movie.start()

    def hide_loading_overlay(self):
        self.loading_overlay.setVisible(False)
        if hasattr(self, 'loading_movie') and self.loading_movie:
            self.loading_movie.stop()

    def init_ui(self):
        layout = self.layout
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(12)

        # 邮箱管理区域
        account_management_layout = QHBoxLayout()
        account_management_layout.setSpacing(16)
        account_management_layout.setContentsMargins(0, 0, 0, 0)

        # 邮箱选择区域
        email_selection_layout = QVBoxLayout()
        self.combo_emails = QComboBox()
        self.combo_emails.setMinimumWidth(250)
        self.combo_emails.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for acc in self.service.accounts:
            self.combo_emails.addItem(acc["email"])

        # 复制邮箱按钮
        copy_layout = QHBoxLayout()
        copy_layout.setContentsMargins(0, 0, 0, 0)
        copy_layout.setSpacing(4)
        copy_layout.addWidget(self.combo_emails)
        self.btn_copy_email = QPushButton("复制邮箱")
        self.btn_copy_email.setToolTip("复制当前邮箱到剪贴板")
        copy_layout.addWidget(self.btn_copy_email)
        email_selection_layout.addLayout(copy_layout)
        account_management_layout.addLayout(email_selection_layout)

        # 邮箱操作按钮区域
        email_buttons_layout = QVBoxLayout()
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        self.btn_generate = QPushButton("生成邮箱")
        self.btn_delete = QPushButton("删除邮箱")
        buttons_layout.addWidget(self.btn_generate)
        buttons_layout.addWidget(self.btn_delete)
        email_buttons_layout.addLayout(buttons_layout)
        account_management_layout.addLayout(email_buttons_layout)

        # 刷新控制区域
        refresh_control_layout = QVBoxLayout()
        refresh_buttons_layout = QHBoxLayout()
        refresh_buttons_layout.setSpacing(8)
        self.btn_refresh = QPushButton("刷新邮件")
        self.chk_auto_refresh = QCheckBox("自动刷新")
        refresh_buttons_layout.addWidget(self.btn_refresh)
        refresh_buttons_layout.addWidget(self.chk_auto_refresh)
        refresh_control_layout.addLayout(refresh_buttons_layout)
        account_management_layout.addLayout(refresh_control_layout)

        layout.addLayout(account_management_layout)

        # 邮件显示区域 - 使用分割器
        mail_display_splitter = QSplitter(Qt.Orientation.Horizontal)
        mail_display_splitter.setHandleWidth(8)

        # 左侧邮件列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        mail_list_header = QHBoxLayout()
        mail_list_header.setSpacing(8)
        mail_list_header.addWidget(QLabel("邮件列表"))
        self.mail_count_label = QLabel("0 封邮件")
        mail_list_header.addWidget(self.mail_count_label)
        mail_list_header.addStretch()
        left_layout.addLayout(mail_list_header)

        self.list_mails = QListWidget()
        self.list_mails.setAlternatingRowColors(True)
        self.list_mails.setMinimumWidth(220)
        self.list_mails.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.list_mails)
        left_widget.setMinimumWidth(240)
        left_widget.setMaximumWidth(400)

        # 右侧邮件内容
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.addWidget(QLabel("邮件内容"))

        self.txt_mail_content = QTextEdit()
        self.txt_mail_content.setReadOnly(True)
        self.txt_mail_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.txt_mail_content)
        right_widget.setMinimumWidth(350)

        # 添加到分割器
        mail_display_splitter.addWidget(left_widget)
        mail_display_splitter.addWidget(right_widget)
        mail_display_splitter.setSizes([320, 680])

        layout.addWidget(mail_display_splitter)

    def setup_connections(self):
        self.btn_generate.clicked.connect(self.generate_email)
        self.btn_delete.clicked.connect(self.delete_account)
        self.btn_refresh.clicked.connect(self.refresh_mails)
        self.combo_emails.currentTextChanged.connect(self.switch_account)
        self.list_mails.itemClicked.connect(self.show_email_content)
        self.chk_auto_refresh.toggled.connect(self.toggle_auto_refresh)
        self.btn_copy_email.clicked.connect(self.copy_email)

    def generate_email(self):
        try:
            email = self.service.create_account()
            self.combo_emails.addItem(email)
            self.combo_emails.setCurrentText(email)
            self.txt_mail_content.clear()
            self.refresh_mails()
        except Exception as e:
            self.service.log(f"生成邮箱失败: {str(e)}", "error")

    def switch_account(self, email):
        if email:
            try:
                self.service.switch_account(email)
                self.txt_mail_content.clear()
                self.refresh_mails()
            except Exception as e:
                self.service.log(f"切换邮箱失败: {str(e)}")

    def refresh_mails(self):
        if not self.combo_emails.currentText():
            self.mail_count_label.setText("0 封邮件")
            return

        self.list_mails.clear()
        self.mail_count_label.setText("加载中...")

        try:
            # 启动异步线程加载邮件
            self.mail_thread = RandomMailLoadThread(self.service)
            self.mail_thread.mails_loaded.connect(self.on_mails_loaded)
            self.mail_thread.error_occurred.connect(self.on_mail_load_error)
            self.mail_thread.start()
        except Exception as e:
            self.mail_count_label.setText("加载失败")
            self.service.log(f"启动邮件加载线程失败: {str(e)}", "error")

    def on_mails_loaded(self, emails):
        self.list_mails.clear()
        for mail in emails:
            item = QListWidgetItem()
            item.setSizeHint(QSize(self.list_mails.viewport().width() - 20, 70))
            item.setData(Qt.ItemDataRole.UserRole, mail["id"])
            sender_name = mail['from']['name'] or mail['from']['address']
            subject = mail['subject'] or "(无主题)"
            time_str = mail['createdAt'][:19].replace('T', ' ')
            widget = MailListItemWidget(subject, sender_name, time_str)
            self.list_mails.addItem(item)
            self.list_mails.setItemWidget(item, widget)
        self.mail_count_label.setText(f"{len(emails)} 封邮件")

    def on_mail_load_error(self, msg):
        self.mail_count_label.setText("加载失败")
        self.service.log(f"邮件加载失败: {msg}", "error")

    def show_email_content(self, item):
        mail_id = item.data(Qt.ItemDataRole.UserRole)
        self._last_mail_id = mail_id
        self.txt_mail_content.setPlainText("正在加载邮件内容...")
        self.show_loading_overlay()
        self.content_thread.load_mail(mail_id)

    def on_mail_content_loaded(self, html, mail_id):
        from PyQt6.QtWidgets import QApplication
        # 只处理最后一次请求的邮件内容
        if mail_id != self._last_mail_id:
            return
        if len(html) > 12*1024 or '内容过大' in html or '无法展示' in html:
            self.txt_mail_content.setPlainText("内容过大或复杂，无法展示")
        else:
            self.txt_mail_content.setPlainText("正在渲染邮件内容...")
            QApplication.processEvents()
            self.txt_mail_content.setHtml(html)
            QApplication.processEvents()
        self.hide_loading_overlay()

    def on_mail_content_error(self, msg):
        self.txt_mail_content.setPlainText(f"加载邮件内容失败: {msg}")
        self.hide_loading_overlay()

    def delete_account(self):
        email = self.combo_emails.currentText()
        if not email:
            return

        try:
            self.service.delete_account(email)
            idx = self.combo_emails.findText(email)
            self.combo_emails.removeItem(idx)
            self.txt_mail_content.clear()
            self.refresh_mails()
        except Exception as e:
            self.service.log(f"删除邮箱失败: {str(e)}", "error")

    def toggle_auto_refresh(self, enabled):
        if enabled:
            self.auto_refresh_timer.start(5000)
        else:
            self.auto_refresh_timer.stop()

    def copy_email(self):
        email = self.combo_emails.currentText()
        if email:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(email)
        else:
            self.service.log("无邮箱可复制", "error")

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        self.show_main_log_area()