import sys
import re
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QApplication, QMainWindow, QListWidgetItem,
                               QMessageBox)

from mail_service import MailTM
from ui_email_tool import Ui_MainWindow


class EmailToolApp(QMainWindow):
    def __init__(self):
        super().__init__()
        QCoreApplication.setApplicationVersion("1.0.0")
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.mail_service = MailTM()
        # 将加载的历史邮箱添加到comboBox
        for account in self.mail_service.accounts:
            self.ui.comboEmails.addItem(account["email"])

        # 如果有历史邮箱，设置当前选中项
        if self.mail_service.accounts:
            self.ui.comboEmails.setCurrentIndex(0)
        # 初始化UI连接
        self.setup_connections()

        # 初始化定时器
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_mails)

        # 初始状态
        self.toggle_auto_refresh(self.ui.autoRefreshCheckbox.isChecked())

        # 调整分割器比例
        self.ui.splitter.setSizes([300, 500])

    def setup_connections(self):
        """设置所有UI信号连接"""
        self.ui.listMails.itemClicked.connect(self.show_email_content)
        self.ui.btnGenerate.clicked.connect(self.generate_email)
        self.ui.btnCopy.clicked.connect(self.copy_email)
        self.ui.btnRefresh.clicked.connect(self.refresh_mails)
        self.ui.comboEmails.currentTextChanged.connect(self.switch_account)
        self.ui.autoRefreshCheckbox.toggled.connect(self.toggle_auto_refresh)
        self.ui.btnDelete.clicked.connect(self.delete_account)
    def toggle_auto_refresh(self, enabled):
        """切换自动刷新状态"""
        if enabled:
            self.auto_refresh_timer.start(5000)
            self.update_status("自动刷新已启用 (5秒)")
        else:
            self.auto_refresh_timer.stop()
            self.update_status("自动刷新已禁用")

    def generate_email(self):
        try:
            email = self.mail_service.create_account()
            self.ui.comboEmails.addItem(email)
            self.ui.comboEmails.setCurrentText(email)
            self.update_status(f"已生成: {email}")
            self.ui.txtMailContent.clear()
            self.refresh_mails()
        except Exception as e:
            self.show_error(str(e))

    def switch_account(self, email):
        if email:
            try:
                self.mail_service.switch_account(email)
                self.update_status(f"已切换到: {email}")
                self.ui.txtMailContent.clear()
                self.refresh_mails()
            except Exception as e:
                self.show_error(str(e))

    def refresh_mails(self):
        if not self.ui.comboEmails.currentText():
            return

        try:
            self.ui.listMails.clear()
            emails = self.mail_service.get_emails()

            for mail in emails:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, mail["id"])  # 存储邮件ID

                # 格式化显示
                text = (
                    f"📧 {mail['from']['name'] or mail['from']['address']}\n"
                    f"主题: {mail['subject']}\n"
                    f"时间: {mail['createdAt'][:19].replace('T', ' ')}"
                )
                item.setText(text)
                self.ui.listMails.addItem(item)

            self.update_status(
                f"已加载 {len(emails)} 封邮件 (自动刷新: {'开启' if self.ui.autoRefreshCheckbox.isChecked() else '关闭'})")

            # 自动显示第一封邮件
            if emails:
                self.ui.listMails.setCurrentRow(0)
                self.show_email_content(self.ui.listMails.currentItem())

        except Exception as e:
            self.show_error(str(e))

    def show_email_content(self, item):
        """显示选中邮件的内容"""
        if not item:
            return

        mail_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            html_content = self.mail_service.get_email_content(mail_id)

            # # 提取验证码（6位数字）
            # code = self.extract_verification_code(html_content)
            # if code:
            #     html_content += f'<div style="color:#4CAF50;font-size:16px;">验证码: {code}</div>'

            # 显示HTML内容
            self.ui.txtMailContent.setHtml(html_content)
            self.ui.txtMailContent.moveCursor(QTextCursor.MoveOperation.Start)

        except Exception as e:
            self.show_error(str(e))

    def extract_verification_code(self, text):
        """从邮件内容提取验证码"""
        match = re.search(r'\b\d{6}\b', text)
        return match.group() if match else None

    def copy_email(self):
        if email := self.ui.comboEmails.currentText():
            QApplication.clipboard().setText(email)
            self.update_status("邮箱已复制到剪贴板")

    def update_status(self, message):
        self.ui.labelStatus.setText(f"状态: {message}")

    def show_error(self, message):
        QMessageBox.critical(self, "错误", message)
        self.update_status(f"错误: {message}")

    def delete_account(self):
        """删除当前选中的邮箱账户"""
        current_email = self.ui.comboEmails.currentText()
        if not current_email:
            return

        reply = QMessageBox.question(
            self, '确认删除',
            f'确定要删除邮箱 {current_email} 吗？此操作不可撤销！',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从服务中删除
                self.mail_service.delete_account(current_email)

                # 从UI中删除
                index = self.ui.comboEmails.findText(current_email)
                if index >= 0:
                    self.ui.comboEmails.removeItem(index)

                # 清空邮件列表和内容
                self.ui.listMails.clear()
                self.ui.txtMailContent.clear()

                self.update_status(f"已删除邮箱: {current_email}")
            except Exception as e:
                self.show_error(str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmailToolApp()
    window.show()
    sys.exit(app.exec())