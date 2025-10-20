# random_mail_window.py
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
                             QListWidget, QCheckBox, QListWidgetItem, QSplitter,
                             QWidget, QSizePolicy, QApplication, QMessageBox)

# 动态导入，确保兼容性
try:
    from pos_tool_new.main import BaseTabWidget
    from .random_mail_service import RandomMailService
    from pos_tool_new.work_threads import RandomMailLoadThread, ReusableMailContentThread
except ImportError:
    # 备用导入方案，防止模块找不到
    BaseTabWidget = object
    RandomMailService = object
    RandomMailLoadThread = object
    ReusableMailContentThread = object

NO_EMAIL_PLACEHOLDER = "暂无可用邮箱"


class RandomMailTabWidget(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__("随机邮箱", parent)
        self.loading_movie = None
        self.loading_label = None
        self.loading_overlay = None
        self.service = RandomMailService()
        self.mail_threads = []  # 用于保存所有 mail_thread 实例
        self._current_emails = []  # 缓存当前邮件列表
        self._is_loading = False  # 防止重复加载
        # 所有实例属性提前声明为 None
        self.combo_emails = None
        self.btn_copy_email = None
        self.btn_generate = None
        self.btn_delete = None
        self.mail_count_label = None
        self.chk_auto_refresh = None
        self.btn_refresh = None
        self.list_mails = None
        self.txt_mail_content = None
        self.content_thread = None
        self.auto_refresh_timer = None
        self._last_mail_id = None

        self.init_ui()
        self.setup_connections()

        # 延迟初始化，避免界面卡顿
        QTimer.singleShot(100, self.delayed_init)

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_mails)
        self.toggle_auto_refresh(False)

        self.init_loading_overlay()  # 初始化加载蒙层
        self.content_thread = ReusableMailContentThread(self.service)
        self.content_thread.mail_content_loaded.connect(self.on_mail_content_loaded)
        self.content_thread.error_occurred.connect(self.on_mail_content_error)
        self._last_mail_id = None

    def delayed_init(self):
        """延迟初始化，提高界面响应速度"""
        if hasattr(self.service, 'accounts') and self.service.accounts:
            self.combo_emails.clear()
            for acc in self.service.accounts:
                self.combo_emails.addItem(acc["email"])
            if self.combo_emails.count() > 0:
                self.combo_emails.setCurrentIndex(0)
                self.refresh_mails()
        else:
            self.combo_emails.clear()
            self.combo_emails.addItem(NO_EMAIL_PLACEHOLDER)
            self.list_mails.clear()
            tip_item = QListWidgetItem("暂无邮件")
            tip_item.setFlags(Qt.ItemFlag.NoItemFlags)
            tip_item.setForeground(Qt.GlobalColor.gray)
            self.list_mails.addItem(tip_item)
            self.mail_count_label.setText("0 封邮件")
            self.txt_mail_content.clear()
        self.update_delete_button_state()

    def init_loading_overlay(self):
        """初始化加载中蒙层"""
        self.loading_overlay = QWidget(self)
        self.loading_overlay.setStyleSheet("""
            background: rgba(255,255,255,0.9);
            border-radius: 8px;
        """)
        self.loading_overlay.setVisible(False)
        self.loading_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.loading_overlay.setGeometry(self.rect())

        layout = QVBoxLayout(self.loading_overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.loading_label = QLabel("加载中...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #34495e;
                font-weight: bold;
            }
        """)

        # 尝试加载gif，如果失败则使用文字
        try:
            gif_paths = [
                "../UI/loading.gif",
                "./UI/loading.gif",
                "UI/loading.gif",
                os.path.join(os.path.dirname(__file__), "../UI/loading.gif"),
                os.path.join(os.path.dirname(__file__), "UI/loading.gif")
            ]
            for gif_path in gif_paths:
                if os.path.exists(gif_path):
                    self.loading_movie = QMovie(gif_path)
                    if self.loading_movie.isValid():
                        from PyQt6.QtCore import QSize
                        self.loading_movie.setScaledSize(QSize(128, 128))  # 设置动画缩放尺寸
                        loading_gif = QLabel()
                        loading_gif.setFixedSize(128, 128)  # 设置标签固定尺寸
                        loading_gif.setMovie(self.loading_movie)
                        loading_gif.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        layout.addWidget(loading_gif)
                        break
        except Exception as e:
            print(f"加载动画失败: {e}")

        layout.addWidget(self.loading_label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(self.rect())

    def show_loading_overlay(self, text="加载中..."):
        """显示加载蒙层"""
        self.loading_label.setText(text)
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.setVisible(True)
        self.loading_overlay.raise_()
        if hasattr(self, 'loading_movie') and self.loading_movie:
            self.loading_movie.start()
        QApplication.processEvents()  # 确保界面更新

    def hide_loading_overlay(self):
        """隐藏加载蒙层"""
        self.loading_overlay.setVisible(False)
        if hasattr(self, 'loading_movie') and self.loading_movie:
            self.loading_movie.stop()

    def init_ui(self):
        """初始化界面"""
        layout = self.layout
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 邮箱管理区域
        account_management_layout = QHBoxLayout()
        account_management_layout.setSpacing(12)
        account_management_layout.setContentsMargins(0, 0, 0, 0)

        # 邮箱选择区域
        email_selection_layout = QVBoxLayout()
        email_selection_layout.setSpacing(4)

        copy_layout = QHBoxLayout()
        copy_layout.setContentsMargins(0, 0, 0, 0)
        copy_layout.setSpacing(6)

        self.combo_emails = QComboBox()
        self.combo_emails.setMinimumWidth(280)
        self.combo_emails.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        copy_layout.addWidget(self.combo_emails)

        self.btn_copy_email = QPushButton("📋 复制")
        self.btn_copy_email.setToolTip("复制当前邮箱到剪贴板")
        copy_layout.addWidget(self.btn_copy_email)

        email_selection_layout.addLayout(copy_layout)
        account_management_layout.addLayout(email_selection_layout)

        # 邮箱操作按钮区域
        email_buttons_layout = QVBoxLayout()
        email_buttons_layout.setSpacing(4)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.btn_generate = QPushButton("🆕 生成邮箱")
        self.btn_generate.setToolTip("生成新的随机邮箱地址")

        self.btn_delete = QPushButton("🗑️ 删除邮箱")
        self.btn_delete.setToolTip("删除当前选中的邮箱")

        buttons_layout.addWidget(self.btn_generate)
        buttons_layout.addWidget(self.btn_delete)
        email_buttons_layout.addLayout(buttons_layout)
        account_management_layout.addLayout(email_buttons_layout)

        # 刷新控制区域
        refresh_control_layout = QVBoxLayout()
        refresh_control_layout.setSpacing(4)

        refresh_buttons_layout = QHBoxLayout()
        refresh_buttons_layout.setSpacing(8)

        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.setToolTip("手动刷新邮件列表")

        self.chk_auto_refresh = QCheckBox("自动刷新(5s)")
        self.chk_auto_refresh.setToolTip("每5秒自动刷新邮件列表")

        refresh_buttons_layout.addWidget(self.btn_refresh)
        refresh_buttons_layout.addWidget(self.chk_auto_refresh)
        refresh_control_layout.addLayout(refresh_buttons_layout)
        account_management_layout.addLayout(refresh_control_layout)

        layout.addLayout(account_management_layout)

        # 邮件显示区域 - 使用分割器
        mail_display_splitter = QSplitter(Qt.Orientation.Horizontal)
        mail_display_splitter.setHandleWidth(4)
        mail_display_splitter.setStyleSheet("""
            QSplitter::handle {
                background: #bdc3c7;
                margin: 1px;
            }
            QSplitter::handle:hover {
                background: #95a5a6;
            }
        """)

        # 左侧邮件列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        mail_list_header = QHBoxLayout()
        mail_list_header.setSpacing(8)

        mail_list_title = QLabel("📧 邮件列表")
        mail_list_header.addWidget(mail_list_title)

        self.mail_count_label = QLabel("0 封邮件")
        mail_list_header.addWidget(self.mail_count_label)
        mail_list_header.addStretch()

        left_layout.addLayout(mail_list_header)

        # 使用默认 QListWidget 样式
        self.list_mails = QListWidget()
        left_layout.addWidget(self.list_mails)
        left_widget.setMinimumWidth(280)
        left_widget.setMaximumWidth(450)

        # 右侧邮件内容
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)

        content_title = QLabel("📄 邮件内容")
        right_layout.addWidget(content_title)

        # 使用 QTextBrowser 替换 QTextEdit
        from PyQt6.QtWidgets import QTextBrowser
        self.txt_mail_content = QTextBrowser()
        self.txt_mail_content.setReadOnly(True)
        self.txt_mail_content.setOpenExternalLinks(True)
        self.txt_mail_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.txt_mail_content)
        right_widget.setMinimumWidth(400)

        # 添加到分割器
        mail_display_splitter.addWidget(left_widget)
        mail_display_splitter.addWidget(right_widget)
        mail_display_splitter.setSizes([300, 700])
        mail_display_splitter.setCollapsible(0, False)
        mail_display_splitter.setCollapsible(1, False)

        layout.addWidget(mail_display_splitter)

    def setup_connections(self):
        """设置信号连接"""
        self.btn_generate.clicked.connect(self.generate_email)
        self.btn_delete.clicked.connect(self.delete_account)
        self.btn_refresh.clicked.connect(self.refresh_mails)
        self.combo_emails.currentTextChanged.connect(self.switch_account)
        self.list_mails.itemClicked.connect(self.show_email_content)
        self.chk_auto_refresh.toggled.connect(self.toggle_auto_refresh)
        self.btn_copy_email.clicked.connect(self.copy_email)

    def update_delete_button_state(self):
        """根据邮箱列表内容更新删除按钮状态"""
        current_text = self.combo_emails.currentText()
        if current_text == NO_EMAIL_PLACEHOLDER or not current_text:
            self.btn_delete.setEnabled(False)
        else:
            self.btn_delete.setEnabled(True)

    def generate_email(self):
        """生成新邮箱（防止频繁点击）"""
        self.btn_generate.setEnabled(False)  # 禁用按钮，防止重复点击
        try:
            self.show_loading_overlay("正在生成邮箱...")
            email = self.service.create_account()
            # 移除“暂无可用邮箱”选项（如果存在）
            idx = self.combo_emails.findText(NO_EMAIL_PLACEHOLDER)
            if idx >= 0:
                self.combo_emails.removeItem(idx)
            self.combo_emails.addItem(email)
            self.combo_emails.setCurrentText(email)
            self.txt_mail_content.clear()
            self.refresh_mails()
            self.hide_loading_overlay()
            self.update_delete_button_state()
        except Exception as e:
            self.hide_loading_overlay()
            # 针对 token 相关错误友好提示
            err_msg = str(e)
            if 'token' in err_msg.lower():
                self.show_error_message("操作过于频繁或授权失效", "请稍后再试，或重新登录。")
            else:
                self.service.log(f"生成邮箱失败: {err_msg}", "error")
                self.show_error_message("生成邮箱失败", err_msg)
        finally:
            # 1秒后恢复按钮可点击
            QTimer.singleShot(5000, lambda: self.btn_generate.setEnabled(True))

    def switch_account(self, email):
        """切换邮箱账户"""
        # 如果是提示语或无效邮箱，直接返回
        if not email or email == NO_EMAIL_PLACEHOLDER:
            self.update_delete_button_state()
            return
        if not self._is_loading:
            try:
                self.service.switch_account(email)
                self.txt_mail_content.clear()
                self.refresh_mails()
            except ValueError as ve:
                self.service.log(f"切换邮箱失败: {str(ve)}", "error")
                self.show_error_message("切换邮箱失败", str(ve))
            except Exception as e:
                self.service.log(f"切换邮箱失败: {str(e)}", "error")
                self.show_error_message("切换邮箱失败", str(e))
        self.update_delete_button_state()

    def refresh_mails(self):
        """刷新邮件列表"""
        if self._is_loading or not self.combo_emails.currentText():
            self.mail_count_label.setText("0 封邮件")
            return

        self._is_loading = True
        self.list_mails.clear()
        self.mail_count_label.setText("加载中...")
        self.btn_refresh.setEnabled(False)

        try:
            # 启动异步线程加载邮件
            mail_thread = RandomMailLoadThread(self.service)
            mail_thread.mails_loaded.connect(self.on_mails_loaded)
            mail_thread.error_occurred.connect(self.on_mail_load_error)
            mail_thread.finished.connect(self.on_mail_load_finished)
            self.mail_threads.append(mail_thread)
            mail_thread.start()
        except Exception as e:
            self.on_mail_load_error(str(e))

    def on_mails_loaded(self, emails):
        """邮件加载完成"""
        self._current_emails = emails
        self.list_mails.clear()

        for mail in emails:
            sender_name = mail['from']['name'] or mail['from']['address']
            subject = mail['subject'] or "(无主题)"
            time_str = mail['createdAt'][:19].replace('T', ' ')
            # 多行文本显示邮件信息，并在每封邮件后加分割线
            item_text = f"主题: {subject}\n发件人: {sender_name}\n时间: {time_str}\n{'-' * 30}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, mail["id"])
            self.list_mails.addItem(item)

        self.mail_count_label.setText(f"{len(emails)} 封邮件")

    def on_mail_load_error(self, msg):
        """邮件加载错误"""
        self.mail_count_label.setText("加载失败")
        self.service.log(f"邮件加载失败: {msg}", "error")
        self.show_error_message("邮件加载失败", msg)

    def on_mail_load_finished(self):
        """邮件加载线程结束"""
        self._is_loading = False
        self.btn_refresh.setEnabled(True)
        # 清理完成的线程
        self.mail_threads = [t for t in self.mail_threads if t.isRunning()]

    def show_email_content(self, item):
        """显示邮件内容"""
        if not item:
            return

        mail_id = item.data(Qt.ItemDataRole.UserRole)
        self._last_mail_id = mail_id
        self.txt_mail_content.setPlainText("正在加载邮件内容...")
        self.show_loading_overlay("加载邮件内容...")

        try:
            self.content_thread.load_mail(mail_id)
        except Exception as e:
            self.on_mail_content_error(str(e))

    def on_mail_content_loaded(self, html, mail_id):
        """邮件内容加载完成"""
        from PyQt6.QtWidgets import QApplication

        # 只处理最后一次请求的邮件内容
        if mail_id != self._last_mail_id:
            return

        try:
            self.txt_mail_content.setPlainText("正在渲染邮件内容...")
            QApplication.processEvents()

            # 直接渲染HTML内容，无论大小或格式
            if html and html.strip():
                self.txt_mail_content.setHtml(f"""
                    <div style="font-family: 'Microsoft YaHei', Arial, sans-serif; 
                               font-size: 13px; line-height: 1.5; color: #2c3e50;">
                        {html}
                    </div>
                """)
            else:
                self.txt_mail_content.setPlainText("邮件内容为空")

            QApplication.processEvents()
        except Exception as e:
            self.txt_mail_content.setPlainText(f"渲染邮件内容时出错: {str(e)}")
        finally:
            self.hide_loading_overlay()

    def on_mail_content_error(self, msg):
        """邮件内容加载错误"""
        self.txt_mail_content.setPlainText(f"加载邮件内容失败: {msg}")
        self.hide_loading_overlay()
        self.show_error_message("邮件内容加载失败", msg)

    def delete_account(self):
        """删除邮箱账户"""
        email = self.combo_emails.currentText()
        if not email:
            return

        # 确认对话框
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除邮箱 {email} 吗？\n此操作不可撤销！",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.service.delete_account(email)
                idx = self.combo_emails.findText(email)
                if idx >= 0:
                    self.combo_emails.removeItem(idx)
                self.txt_mail_content.clear()

                # 如果还有邮箱，切换到第一个
                if self.combo_emails.count() > 0:
                    self.combo_emails.setCurrentIndex(0)
                else:
                    # 没有邮箱时，清空邮件列表和标签
                    self.list_mails.clear()
                    self.mail_count_label.setText("0 封邮件")
                    self.txt_mail_content.clear()
                    self.combo_emails.addItem(NO_EMAIL_PLACEHOLDER)
                    self.combo_emails.setCurrentIndex(0)
                self.update_delete_button_state()
            except Exception as e:
                self.service.log(f"删除邮箱失败: {str(e)}", "error")
                self.show_error_message("删除邮箱失败", str(e))

    def toggle_auto_refresh(self, enabled):
        """切换自动刷新"""
        if enabled:
            self.auto_refresh_timer.start(5000)  # 5秒刷新
            self.btn_refresh.setText("🔄 停止自动")
            self.btn_refresh.clicked.disconnect()
            self.btn_refresh.clicked.connect(self.stop_auto_refresh)
        else:
            self.auto_refresh_timer.stop()
            self.btn_refresh.setText("🔄 刷新")
            self.btn_refresh.clicked.disconnect()
            self.btn_refresh.clicked.connect(self.refresh_mails)

    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.chk_auto_refresh.setChecked(False)

    def copy_email(self):
        """复制邮箱到剪贴板"""
        email = self.combo_emails.currentText()
        if email:
            try:
                QApplication.clipboard().setText(email)
                # 显示复制成功提示
                self.btn_copy_email.setText("✓ 已复制")
                QTimer.singleShot(1000, lambda: self.btn_copy_email.setText("📋 复制"))
            except Exception as e:
                self.service.log(f"复制失败: {str(e)}", "error")
        else:
            self.service.log("无邮箱可复制", "warning")

    def show_error_message(self, title, message):
        """显示错误消息对话框"""
        QMessageBox.warning(self, title, message)

    def showEvent(self, event):
        """显示事件处理"""
        super().showEvent(event)
        if hasattr(self, 'hide_main_log_area'):
            self.hide_main_log_area()

    def hideEvent(self, event):
        """隐藏事件处理"""
        super().hideEvent(event)
        if hasattr(self, 'show_main_log_area'):
            self.show_main_log_area()

    def closeEvent(self, event):
        """关闭事件处理"""
        # 安全停止所有线程
        self.auto_refresh_timer.stop()

        for thread in getattr(self, 'mail_threads', []):
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # 等待1秒

        if hasattr(self, 'content_thread') and self.content_thread.isRunning():
            self.content_thread.quit()
            self.content_thread.wait(1000)

        super().closeEvent(event)
