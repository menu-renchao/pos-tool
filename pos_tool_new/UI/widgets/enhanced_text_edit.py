from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QTextEdit


class EnhancedTextEdit(QTextEdit):
    """增强的文本编辑框，支持彩色日志"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def append_colored_text(self, text: str, color: str = "#000000"):
        """添加带颜色的文本"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format = QTextCharFormat()
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        cursor.insertText(text + "\n")

        # 自动滚动到底部
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
