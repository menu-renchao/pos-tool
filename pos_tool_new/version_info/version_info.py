from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox


class VersionInfoDialog(QDialog):
    """版本信息对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("版本信息")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # 版本信息显示区域
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        layout.addWidget(self.text_browser)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.load_version_info()

    def load_version_info(self):
        """加载版本信息"""
        try:
            from pos_tool_new.main import resource_path
            html_path = resource_path("version_info/version_info.html")
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
            self.text_browser.setHtml(html)
        except Exception:
            self.text_browser.setHtml("<h2>版本信息文件未找到</h2>")
