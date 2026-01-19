"""
应用程序样式表模块
"""


def get_stylesheet() -> str:
    """获取应用程序样式表"""
    return """
        QMainWindow {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f8f9fa, stop: 1 #e9ecef);
        }
        QGroupBox {
            font-weight: 600;
            font-size: 12px;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            margin-top: 0.5ex;
            padding-top: 8px;
            background: white;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 6px 0 6px;
            color: #495057;
        }
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #7fbfff, stop: 1 #4a90e2);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: 500;
            font-size: 11px;
        }
        QPushButton:focus {
            outline: none;
        }
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #6bacff, stop: 1 #3a7bc8);
        }
        QPushButton:pressed {
            background: #2c6aa8;
        }
        QPushButton:disabled {
            background: #a0a0a0;
            color: #d0d0d0;
        }
        QTabWidget::pane {
            border: 1px solid #dee2e6;
            border-radius: 6px;
            background: white;
            margin-top: -1px;
            padding: 4px;
            min-width: 0px;
        }
        QTabBar::tab {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 4px 8px;
            margin-right: 2px;
            font-size: 11px;
            color: #495057;
        }
        QTabBar::tab:selected {
            background: white;
            border-bottom-color: white;
            color: #007bff;
            font-weight: 600;
        }
        QTabBar::tab:!selected {
            margin-top: 2px;
            background: #e9ecef;
        }
        QTabBar::tab:hover:!selected {
            background: #dee2e6;
        }
        QTextEdit {
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 11px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px;
            background: white;
            selection-background-color: #007bff;
        }
        QProgressBar {
            border: 1px solid #ced4da;
            border-radius: 4px;
            text-align: center;
            background: #f8f9fa;
            height: 20px;
            color: #495057;
            font-size: 10px;
            font-weight: 500;
        }
        QToolTip {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 12px;
            opacity: 240;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 #00b09b, stop: 1 #96c93d);
            border-radius: 3px;
            margin: 0.5px;
        }
        QToolBar {
            background: #f8f9fa;
            border: none;
            border-bottom: 1px solid #dee2e6;
            spacing: 4px;
            padding: 4px;
        }
        QToolBar::separator {
            background: #dee2e6;
            width: 1px;
            margin: 0 4px;
        }
    """


def get_clear_button_style() -> str:
    """获取清除按钮样式"""
    return """
        QPushButton {
            background: #6c757d;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 10px;
        }
        QPushButton:hover {
            background: #5a6268;
        }
    """


def get_speed_label_style() -> str:
    """获取速度标签样式"""
    return """
        QLabel {
            font-size: 10px;
            color: #28a745;
            font-weight: 500;
            background: #d4edda;
            padding: 2px 6px;
            border-radius: 3px;
            border: 1px solid #c3e6cb;
        }
    """


def get_bottom_widget_style() -> str:
    """获取底部部件样式"""
    return """
        background: #f8f9fa;
        border-top: 1px solid #dee2e6;
        border-bottom-left-radius: 8px;
        border-bottom-right-radius: 8px;
    """


def get_splitter_style() -> str:
    """获取分割条样式"""
    return '''
        QSplitter::handle:vertical {
            height: 12px;
            background: transparent;
        }
        QSplitter::handle:vertical:hover {
            background: #f0f0f0;
        }
        QSplitter::handle:vertical:pressed {
            background: #e0e0e0;
        }
    '''
