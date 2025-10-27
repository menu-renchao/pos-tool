from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from pos_tool_new.work_threads import  RemoteTailLogThread

class TailLogWindow(QDialog):
    def __init__(self, file_path, ssh_params=None, remote=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"实时日志 - {file_path}")
        self.resize(800, 500)
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)
        self.stop_btn = QPushButton("停止实时")
        self.stop_btn.clicked.connect(lambda: self.close())
        self.layout.addWidget(self.stop_btn)
        self.thread = None
        if remote and ssh_params:
            service, host, username, password = ssh_params[:4]  # 修正：解包4个参数
            self.thread = RemoteTailLogThread(service, host, username, password, file_path)
        self.thread.log_updated.connect(self.append_log)
        self.thread.start()

    def append_log(self, text):
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            self.thread.wait()
        event.accept()
