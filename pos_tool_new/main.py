import os
import sys
import tempfile
import time
from typing import Optional

from PyQt6.QtWidgets import QListWidget

from pos_tool_new.modern_splash import ModernSplashScreen
from pos_tool_new.update_dialog import check_and_update_exe
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, QRectF
from PyQt6.QtGui import QFont, QPalette, QTextCharFormat, QTextCursor, QAction, QIcon, QColor, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QTextEdit, QPushButton, QHBoxLayout,
    QLabel, QGroupBox, QProgressBar, QMainWindow,
    QMenuBar, QMessageBox, QVBoxLayout, QSplitter, QCheckBox, QDialog, QDialogButtonBox, QLineEdit
)
from PyQt6.QtWidgets import QSplitterHandle
from PyQt6.QtGui import QPainter

from pos_tool_new.backend import Backend
from pos_tool_new.version_info.version_info import VersionInfoDialog
from pos_tool_new.utils.log_manager import global_log_manager
from pos_tool_new.utils.app_config_utils import (
    get_app_config_value, set_app_config_value,
    load_tab_config_from_app, save_tab_config_to_app,
    TAB_ID_MAP, TAB_ID_LIST
)


def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，支持PyInstaller打包后的路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


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


class AnimatedProgressBar(QProgressBar):
    """带动画效果的进度条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def start_animation(self, duration=1000):
        """开始动画"""
        self.animation.setDuration(duration)
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.start()

    def stop_animation(self):
        """停止动画"""
        self.animation.stop()


class CustomSplitterHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        # 画三个点
        color = QColor('#555' if self._hover else '#888')
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        dot_d = 4  # 直径
        spacing = 6
        total_w = dot_d * 3 + spacing * 2
        start_x = (w - total_w) // 2
        cy = h // 2
        for i in range(3):
            cx = start_x + i * (dot_d + spacing) + dot_d // 2
            painter.drawEllipse(cx, cy - dot_d // 2, dot_d, dot_d)


class CustomSplitter(QSplitter):
    def createHandle(self):
        return CustomSplitterHandle(self.orientation(), self)


class GuideOverlay(QWidget):
    """多步骤首次运行引导蒙层"""

    def __init__(self, parent, steps):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("")
        self.steps = steps  # [(控件, 提示文本)]
        self.current_step = 0
        self.tip_label = QLabel(self)
        self.tip_label.setStyleSheet(
            "color: white; font-size: 18px; font-weight: bold; background: rgba(0,0,0,180); border-radius:8px; padding:16px;")
        self.tip_label.setWordWrap(True)  # 关闭自动换行
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setSizePolicy(self.tip_label.sizePolicy().horizontalPolicy(),
                                     self.tip_label.sizePolicy().verticalPolicy())
        self.next_btn = QPushButton(self)
        self.next_btn.setStyleSheet(
            "font-size: 16px; padding: 8px 24px; background: #007bff; color: white; border-radius: 6px;")
        self.next_btn.clicked.connect(self.next_step)
        self.update_step()
        self.setVisible(True)
        self.adjust_overlay_geometry()

    def adjust_overlay_geometry(self):
        # Ensure overlay always matches parent size and is on top
        if self.parentWidget():
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
            self.raise_()

    def showEvent(self, event):
        self.adjust_overlay_geometry()
        super().showEvent(event)

    def update_step(self):
        if self.current_step >= len(self.steps):
            self.finish_guide()
            return
        _, tip = self.steps[self.current_step]
        # 所有步骤统一为深色背景、白色字体、蓝色边框，无icon
        self.tip_label.setText(tip)
        self.tip_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            background: rgba(0,0,0,0.92);
            border: 2px solid #42a5f5;
            border-radius:12px;
            padding:18px;
            box-shadow: 0 2px 12px rgba(66,165,245,0.15);
        """)
        if self.current_step == len(self.steps) - 1:
            self.next_btn.setText("完成")
        else:
            self.next_btn.setText("下一步")
        self.repaint()
        self.update_tip_position()

    def update_tip_position(self):
        # 将tip_label和按钮放在高亮区域下方或中央
        target, _ = self.steps[self.current_step]
        if isinstance(target, QWidget) and target.isVisible():
            rect = target.rect()
            top_left = target.mapToGlobal(rect.topLeft())
            parent_top_left = self.parentWidget().mapToGlobal(QPoint(0, 0))
            rel_pos = top_left - parent_top_left
            # 放在高亮区域下方
            tip_w = min(400, self.width() - 40)
            self.tip_label.setFixedWidth(tip_w)
            self.tip_label.adjustSize()
            tip_h = self.tip_label.height()
            btn_h = 40
            x = rel_pos.x() + (rect.width() - tip_w) // 2
            y = rel_pos.y() + rect.height() + 20
            if y + tip_h + btn_h > self.height():
                y = max(20, rel_pos.y() - tip_h - btn_h - 20)
            self.tip_label.move(max(20, x), y)
            self.next_btn.move(max(20, x), y + tip_h + 10)
            self.next_btn.setFixedWidth(120)
            self.next_btn.setFixedHeight(36)
            self.tip_label.setVisible(True)
            self.next_btn.setVisible(True)
        else:
            # 非QWidget（如QAction），tip居中
            self.tip_label.setFixedWidth(min(400, self.width() - 40))
            self.tip_label.adjustSize()
            tip_h = self.tip_label.height()
            self.tip_label.move((self.width() - self.tip_label.width()) // 2, (self.height() - tip_h) // 2)
            self.next_btn.move((self.width() - 120) // 2, (self.height() + tip_h) // 2 + 10)
            self.next_btn.setFixedWidth(120)
            self.next_btn.setFixedHeight(36)
            self.tip_label.setVisible(True)
            self.next_btn.setVisible(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        target, _ = self.steps[self.current_step]
        # 只对QWidget高亮挖空
        if isinstance(target, QWidget) and target.isVisible():
            rect = target.rect()
            top_left = target.mapToGlobal(rect.topLeft())
            parent_top_left = self.parentWidget().mapToGlobal(QPoint(0, 0))
            rel_pos = top_left - parent_top_left
            highlight_rect = QRect(rel_pos, rect.size())
            path = QPainterPath()
            path.addRect(QRectF(self.rect()))
            path.addRoundedRect(QRectF(highlight_rect), 12, 12)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillPath(path, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QColor(0, 180, 255, 220))
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawRoundedRect(highlight_rect, 12, 12)

    def resizeEvent(self, event):
        self.adjust_overlay_geometry()
        self.update_tip_position()
        super().resizeEvent(event)

    def next_step(self):
        self.current_step += 1
        self.update_step()

    def finish_guide(self):
        self.setVisible(False)
        from pos_tool_new.utils.app_config_utils import set_app_config_value
        set_app_config_value('guide_shown', 'true')


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        from pos_tool_new.utils.app_config_utils import get_app_config_value
        self._sms_service_ip = get_app_config_value('micro_default_ip', None)
        self._sms_service_port = get_app_config_value('micro_default_sms_port', None)
        super().__init__()
        self.finish_timer: Optional[QTimer] = None
        self.log_text: Optional[EnhancedTextEdit] = None
        self.log_group: Optional[QGroupBox] = None
        self.fake_progress: int = 0
        # 初始化短信微服务环境变量，首次启动即生效
        if self._sms_service_ip and self._sms_service_port:
            default_url = f"http://{self._sms_service_ip}:{self._sms_service_port}"
            os.environ['PLAYWRIGHT_SERVER_URL'] = default_url
        else:
            os.environ['PLAYWRIGHT_SERVER_URL'] = ''

        self._init_components()
        self.setup_backend()
        self.setup_ui()

        global_log_manager.log_received.connect(self.log_text.append_colored_text)

        # 首次运行检测
        self.guide_overlay = None
        self.check_and_show_guide_overlay()
        self.check_and_clear_history_exe()

    def check_and_clear_history_exe(self):
        from pos_tool_new.utils.app_config_utils import get_app_config_value, set_app_config_value
        import os
        if get_app_config_value('need_clear_history_files', 'false') == 'true':
            # 删除旧exe
            old_exe_path = get_app_config_value('old_exe_path', '')
            if old_exe_path and os.path.exists(old_exe_path):
                try:
                    os.remove(old_exe_path)
                except Exception as e:
                    pass  # 可加日志
                set_app_config_value('old_exe_path', '')
            set_app_config_value('need_clear_history_files', 'false')

    def _init_components(self):
        """初始化组件"""
        self.progress_timer = QTimer(self)
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("处理中... %p%")

        self.speed_label = QLabel()
        self.speed_label.setVisible(False)
        self.speed_label.setMinimumWidth(120)
        self.speed_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #28a745;
                font-weight: 500;
                background: #d4edda;
                padding: 2px 6px;
                border-radius: 3px;
                border: 1px solid #c3e6cb;
            }
        """)

        # ====== 跑马灯浮层条 ======
        marquee_widget = QWidget()
        marquee_layout = QHBoxLayout(marquee_widget)
        marquee_layout.setContentsMargins(0, 0, 0, 0)
        marquee_layout.setSpacing(0)
        from PyQt6.QtWidgets import QSizePolicy
        self.marquee_bar = QLabel("")
        self.marquee_bar.setMinimumHeight(28)
        self.marquee_bar.setStyleSheet("""
            QLabel {
                background: #fffbe6;
                color: #d48806;
                font-weight: bold;
                font-size: 15px;
                border-bottom: 1px solid #ffe58f;
                padding-left: 16px;
            }
        """)
        self.marquee_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.marquee_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.marquee_bar.setWordWrap(False)
        self.marquee_text = ""
        self.marquee_pos = 0
        self.marquee_timer = QTimer(self)
        self.marquee_timer.timeout.connect(self._scroll_marquee)
        print('[Marquee] QTimer connected to _scroll_marquee')
        global_log_manager.log('[Marquee] QTimer connected to _scroll_marquee', 'debug')
        # 新增关闭按钮
        from PyQt6.QtWidgets import QPushButton
        self.marquee_close_btn = QPushButton("×")
        self.marquee_close_btn.setFixedSize(28, 28)
        self.marquee_close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #d48806;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover {
                background: #ffe58f;
            }
        """)
        self.marquee_close_btn.setToolTip("关闭跑马灯")
        self.marquee_close_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.marquee_close_btn.clicked.connect(self._close_marquee_bar)
        marquee_layout.addWidget(self.marquee_bar, 1)
        marquee_layout.addWidget(self.marquee_close_btn, 0)
        marquee_widget.setMinimumHeight(28)
        marquee_widget.setVisible(False)
        self.marquee_widget = marquee_widget
        self.marquee_closed_by_user = False

    def setup_ui(self):
        """设置UI界面"""
        self._setup_window_properties()
        self.setup_styles()
        self.create_menubar()

        central_widget = self._create_central_widget()
        # ====== 在主布局顶部插入跑马灯浮层条 ======
        layout = central_widget.layout() or central_widget.findChild(QVBoxLayout)
        if layout is not None:
            layout.insertWidget(0, self.marquee_widget)
        else:
            vbox = QVBoxLayout(central_widget)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)
            vbox.addWidget(self.marquee_widget)
            vbox.addWidget(self._create_central_widget())
            central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

        # 安装分割条handle事件过滤器
        handle = self.splitter.handle(1)  # 1为日志区分割条
        handle.installEventFilter(self)
        self._log_collapsed = False
        self._log_last_size = 180  # 默认展开高度

        # 分割条样式：低高度，透明背景，hover略变色
        self.splitter.setStyleSheet('''
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
        ''')

        self._setup_progress_timer()

    def eventFilter(self, obj, event):
        # 分割条handle收起/展开日志区
        if hasattr(self, 'splitter') and obj == self.splitter.handle(1):
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.MouseButtonDblClick or event.type() == QEvent.Type.MouseButtonPress:
                self.toggle_log_area()
                return True
        return super().eventFilter(obj, event)

    def toggle_log_area(self):
        """切换日志区收起/展开"""
        sizes = self.splitter.sizes()
        if not self._log_collapsed:
            # 收起日志区，记录原高度
            self._log_last_size = sizes[1] if sizes[1] > 0 else self._log_last_size
            self.splitter.setSizes([sizes[0] + sizes[1], 0])
            self._log_collapsed = True
        else:
            # 展开日志区，恢复原高度
            total = sum(sizes)
            log_size = self._log_last_size
            main_size = max(0, total - log_size)
            self.splitter.setSizes([main_size, log_size])
            self._log_collapsed = False

    def _setup_window_properties(self):
        """设置窗口属性"""
        self.setWindowIcon(QIcon(resource_path('UI/app.ico')))
        self.setWindowTitle("POS测试工具 v1.5.1.6 by Mansuper")
        self.resize(900, 580)

    def _create_central_widget(self) -> QWidget:
        """创建中央部件"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(True)
        self.tabs.tabBar().tabMoved.connect(self.on_tab_moved)

        # 创建日志区域
        self.create_log_area()

        # 使用自定义分割器
        self.splitter = CustomSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.log_group)
        self.log_group.setMinimumHeight(270)
        self.splitter.setSizes([600, 180])
        main_layout.addWidget(self.splitter)

        # 添加底部部件
        main_layout.addWidget(self._create_bottom_widget())

        # 创建选项卡内容
        self.create_tab_contents()

        return central_widget

    def _create_bottom_widget(self) -> QWidget:
        """创建底部部件"""
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(16, 8, 16, 8)
        bottom_layout.setSpacing(16)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.speed_label)
        bottom_layout.addStretch()

        bottom_widget.setStyleSheet("""
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)

        return bottom_widget

    def _setup_progress_timer(self):
        """设置进度条定时器"""
        self.fake_progress = 0
        self.progress_timer.timeout.connect(self.update_fake_progress)

    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar() or QMenuBar(self)
        # 添加关于菜单
        about_menu = menubar.addMenu("关于(&A)")
        # 添加“检查更新”菜单项
        check_update_action = QAction("检查更新", self)
        check_update_action.triggered.connect(lambda: check_and_update_exe(self))
        about_menu.addAction(check_update_action)

        version_action = QAction("版本信息", self)
        version_action.triggered.connect(self.show_version_info)
        about_menu.addAction(version_action)

        # 添加设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        global_ip_action = QAction("全局IP", self)
        global_ip_action.triggered.connect(self.show_global_ip_dialog)
        settings_menu.addAction(global_ip_action)

        micro_service_action = QAction("微服务", self)
        micro_service_action.triggered.connect(self.show_micro_service_config_dialog)
        settings_menu.addAction(micro_service_action)

        layout_action = QAction("布局", self)
        layout_action.triggered.connect(self.show_layout_config_dialog)
        settings_menu.addAction(layout_action)

        # 添加清空历史war包菜单项
        clear_war_action = QAction("临时war包清理", self)
        clear_war_action.triggered.connect(self.clear_history_war_folders)
        settings_menu.addAction(clear_war_action)

        self.setMenuBar(menubar)

    def show_layout_config_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("布局 - 选择常用Tab")
        layout = QVBoxLayout(dialog)
        config = load_tab_config_from_app()
        tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})
        checkboxes = {}

        # 全选复选框
        select_all_cb = QCheckBox("全选")
        layout.addWidget(select_all_cb)

        # 防止递归更新的标志
        self._updating_checkboxes = False

        def update_select_all_state():
            """更新全选复选框的状态"""
            if self._updating_checkboxes:
                return

            self._updating_checkboxes = True

            # 计算选中的数量
            checked_count = sum(1 for cb in checkboxes.values() if cb.isChecked())
            total_count = len(checkboxes)

            if checked_count == total_count:
                # 全部选中
                select_all_cb.setCheckState(Qt.CheckState.Checked)
            elif checked_count == 0:
                # 全部未选中
                select_all_cb.setCheckState(Qt.CheckState.Unchecked)
            else:
                # 部分选中
                select_all_cb.setCheckState(Qt.CheckState.PartiallyChecked)

            self._updating_checkboxes = False

        def on_select_all_changed(state):
            """全选复选框状态改变时的处理"""
            if self._updating_checkboxes:
                return
            self._updating_checkboxes = True
            if state in [1, 2]:  # Checked
                for cb in checkboxes.values():
                    cb.setChecked(True)
            elif state == 0:  # Unchecked
                for cb in checkboxes.values():
                    cb.setChecked(False)
            # 部分选中状态不需要处理，因为用户不能直接设置部分选中

            self._updating_checkboxes = False
            # 批量设置后，刷新全选复选框状态，确保同步
            update_select_all_state()

        def on_tab_changed():
            """单个tab复选框状态改变时的处理"""
            update_select_all_state()

        # 连接信号
        select_all_cb.stateChanged.connect(on_select_all_changed)

        # 创建tab复选框
        for tid in TAB_ID_LIST:
            cb = QCheckBox(TAB_ID_MAP.get(tid, tid))
            cb.setChecked(tabs_enabled.get(tid, True))
            cb.stateChanged.connect(on_tab_changed)
            layout.addWidget(cb)
            checkboxes[tid] = cb

        # 初始化全选状态
        update_select_all_state()

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        # 显示对话框并处理结果
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tabs_enabled = {tid: cb.isChecked() for tid, cb in checkboxes.items()}
            config = load_tab_config_from_app()
            tab_order = config.get("tab_order", TAB_ID_LIST)
            save_tab_config_to_app(new_tabs_enabled, tab_order)
            self.refresh_tabs()

    def on_tab_moved(self):
        """tab拖拽顺序变化时，保存顺序到tab_config.json"""
        tab_ids = []
        for i in range(self.tabs.count()):
            tab_text = self.tabs.tabText(i)
            for tid, cname in TAB_ID_MAP.items():
                if tab_text == cname:
                    tab_ids.append(tid)
        config = load_tab_config_from_app()
        tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})
        save_tab_config_to_app(tabs_enabled, tab_ids)

    def refresh_tabs(self):
        """移除所有tab并重新加载"""
        while self.tabs.count():
            self.tabs.removeTab(0)
        config = load_tab_config_from_app()
        tab_order = config.get("tab_order", TAB_ID_LIST)
        tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})
        id_to_import = {tid: imp for tid, *imp in self.tab_imports}
        self.tab_imports = [(tid, *id_to_import[tid]) for tid in tab_order if tid in id_to_import]
        for tid, module_path, class_name in self.tab_imports:
            if not tabs_enabled.get(tid, True):
                continue
            try:
                module = __import__(module_path, fromlist=[class_name])
                tab_class = getattr(module, class_name)
                tab_instance = tab_class(self)
                tab_text = TAB_ID_MAP.get(tid, tid)
                self.tabs.addTab(tab_instance, tab_text)
            except (ImportError, AttributeError) as e:
                global_log_manager.log(f"Failed to load tab {tid}: {e}", "error")

    def show_global_ip_dialog(self):
        """弹出全局IP配置窗口（QComboBox方式）"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel
        dialog = QDialog(self)
        dialog.setWindowTitle("配置全局IP")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("请输入全局IP:"))
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems([
            "192.168.0.", "192.168.1.", "10.24.1.",
            "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
        ])
        current_ip = self.get_global_ip()
        if current_ip:
            combo.setCurrentText(current_ip)
        layout.addWidget(combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ip = combo.currentText().strip()
            if ip:
                self.set_global_ip(ip)
                # 同步所有FileConfigTabWidget的host_ip
                for i in range(self.tabs.count()):
                    tab = self.tabs.widget(i)
                    if hasattr(tab, 'set_host_ip') and callable(tab.set_host_ip):
                        tab.set_host_ip(ip)
                QMessageBox.information(self, "提示",
                                        f"全局IP已设置为: {ip}。仅首次会同步到所有选项卡，之后各选项卡可单独修改IP。")

    def get_global_ip(self) -> str:
        """读取全局IP（仅内存，不写文件）"""
        return getattr(self, '_global_ip', '')

    def set_global_ip(self, ip: str):
        """保存全局IP（仅内存，不写文件）"""
        self._global_ip = ip

    def show_version_info(self):
        """显示版本信息"""
        dialog = VersionInfoDialog(self)
        dialog.exec()

    def setup_backend(self):
        """设置后端"""
        self.backend = Backend()
        self.backend.log_signal.connect(lambda msg: self.append_log(msg, "info"))

    def setup_styles(self):
        """设置应用程序样式"""
        app.setStyle("Fusion")

        # 创建调色板
        palette = QPalette()
        palette_configs = [
            (QPalette.ColorRole.Window, QColor(245, 245, 245)),
            (QPalette.ColorRole.WindowText, QColor(33, 37, 41)),
            (QPalette.ColorRole.Base, QColor(255, 255, 255)),
            (QPalette.ColorRole.AlternateBase, QColor(248, 249, 250)),
            (QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220)),
            (QPalette.ColorRole.ToolTipText, QColor(33, 37, 41)),
            (QPalette.ColorRole.Text, QColor(33, 37, 41)),
            (QPalette.ColorRole.Button, QColor(248, 249, 250)),
            (QPalette.ColorRole.ButtonText, QColor(33, 37, 41)),
            (QPalette.ColorRole.BrightText, QColor(220, 53, 69)),
            (QPalette.ColorRole.Highlight, QColor(0, 123, 255)),
            (QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        ]

        for role, color in palette_configs:
            palette.setColor(role, color)

        app.setPalette(palette)
        app.setFont(QFont("Microsoft YaHei", 9))

        self.setStyleSheet(self._get_stylesheet())

    def _get_stylesheet(self) -> str:
        """获取样式表"""
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

    def create_log_area(self):
        """创建日志区域"""
        self.log_group = QGroupBox("📝 操作日志")
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setSpacing(4)
        log_layout.setContentsMargins(6, 6, 6, 6)

        # 日志工具栏
        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()

        clear_btn = QPushButton("🗑️ 清除日志")
        clear_btn.setMaximumWidth(100)
        clear_btn.clicked.connect(self.clear_logs)
        clear_btn.setStyleSheet("""
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
        """)
        log_toolbar.addWidget(clear_btn)
        log_layout.addLayout(log_toolbar)

        # 日志文本区域
        self.log_text = EnhancedTextEdit()
        if self.log_text is not None:
            self.log_text.setMinimumHeight(120)
        log_layout.addWidget(self.log_text)

    def clear_logs(self):
        """清除日志"""
        if self.log_text:
            self.log_text.clear()

    def show_upload_speed(self, speed_text):
        """显示上传速度"""
        self.speed_label.setText(f"📊 {speed_text}")
        self.speed_label.setVisible(True)

    def hide_upload_speed(self):
        """隐藏上传速度"""
        self.speed_label.setVisible(False)

    def setup_progress_animation(self, interval: int):
        """设置进度条动画"""
        self.fake_progress = 0
        self.progress_timer.start(interval)

    def update_fake_progress(self):
        """更新模拟进度"""
        if self.fake_progress < 99:
            self.fake_progress += 1
            self.progress_bar.setValue(self.fake_progress)
        else:
            self.progress_timer.stop()

    def on_restart_finished(self):
        """重启完成处理"""
        # 确保 finish_timer 已初始化且为 QTimer 实例
        if not hasattr(self, 'finish_timer') or self.finish_timer is None:
            self.finish_timer = QTimer(self)
        else:
            self.finish_timer.stop()
            try:
                self.finish_timer.timeout.disconnect()
            except Exception:
                pass
        self.progress_bar.setVisible(True)
        current_value = self.progress_bar.value()
        target_value = 100
        step = max((target_value - current_value) / 30, 1)

        def update_progress():
            nonlocal current_value
            if current_value < target_value:
                current_value += step
                if current_value > target_value:
                    current_value = target_value
                self.progress_bar.setValue(int(current_value))
            else:
                self.finish_timer.stop()
                self.progress_bar.setValue(target_value)
                self.progress_bar.setVisible(False)

        self.finish_timer.timeout.connect(update_progress)
        self.finish_timer.start(20)

    def append_log(self, msg, level="info"):
        """添加日志"""
        global_log_manager.log(msg, level)

    def load_layout_config(self):
        from pos_tool_new.utils.app_config_utils import get_app_config_value
        layout_config = {}
        tab_names = [tab_name for _, _, tab_name in self.tab_imports]
        for tab_name in tab_names:
            value = get_app_config_value(tab_name, None)
            if value is not None:
                layout_config[tab_name] = (value.lower() == 'true')
            else:
                layout_config[tab_name] = True
        return layout_config

    def create_tab_contents(self):
        config = load_tab_config_from_app()
        tab_order = config.get("tab_order", TAB_ID_LIST)
        tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})
        self.tab_imports = [
            ("linux_pos", "pos_tool_new.linux_pos.linux_window", "LinuxTabWidget"),
            ("linux_file_config", "pos_tool_new.linux_file_config.file_config_linux_window", "FileConfigTabWidget"),
            ("win_pos", "pos_tool_new.windows_pos.windows_window", "WindowsTabWidget"),
            ("win_file_config", "pos_tool_new.windows_file_config.file_config_win_window", "WindowsFileConfigTabWidget"),
            ("db_config", "pos_tool_new.db_config.db_config_window", "DbConfigWindow"),
            ("scan_pos", "pos_tool_new.scan_pos.scan_pos_window", "ScanPosTabWidget"),
            ("scan_printer", "pos_tool_new.scan_printer.scan_printer_window", "ScanPrinterTabWidget"),
            ("caller_id", "pos_tool_new.caller_id.caller_window", "CallerIdTabWidget"),
            ("license", "pos_tool_new.license_backup.license_window", "LicenseToolTabWidget"),
            ("download_war", "pos_tool_new.download_war.download_war_window", "DownloadWarTabWidget"),
            ("generate_img", "pos_tool_new.generate_img.generate_img_window", "GenerateImgTabWidget"),
            ("random_mail", "pos_tool_new.random_mail.random_mail_window", "RandomMailTabWidget"),
            ("sms", "pos_tool_new.sms.sms_window", "SmsWindow"),
            ("lan_chat", "pos_tool_new.lan_chat.lan_chat_window", "LanChatTab")
        ]
        id_to_import = {tid: imp for tid, *imp in self.tab_imports}
        self.tab_imports = [(tid, *id_to_import[tid]) for tid in tab_order if tid in id_to_import]
        for tid, module_path, class_name in self.tab_imports:
            if not tabs_enabled.get(tid, True):
                continue
            try:
                module = __import__(module_path, fromlist=[class_name])
                tab_class = getattr(module, class_name)
                tab_instance = tab_class(self)
                tab_text = TAB_ID_MAP.get(tid, tid)
                self.tabs.addTab(tab_instance, tab_text)
            except (ImportError, AttributeError) as e:
                global_log_manager.log(f"Failed to load tab {tid}: {e}", "error")

    def show_micro_service_config_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("微服务配置")
        layout = QVBoxLayout(dialog)
        # IP输入
        ip_layout = QHBoxLayout()
        ip_label = QLabel("服务IP:")
        micro_default_ip = get_app_config_value('micro_default_ip', None)
        ip_edit = QLineEdit()
        ip_edit.setText(self._micro_service_ip if hasattr(self, '_micro_service_ip') else micro_default_ip or '')
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(ip_edit)
        layout.addLayout(ip_layout)
        # 短信服务端口输入
        sms_port_layout = QHBoxLayout()
        sms_port_label = QLabel("短信服务端口:")
        micro_default_sms_port = get_app_config_value('micro_default_sms_port', None)
        sms_port_edit = QLineEdit()
        sms_port_edit.setText(str(self._micro_service_sms_port) if hasattr(self,
                                                                           '_micro_service_sms_port') else micro_default_sms_port or '')
        sms_port_layout.addWidget(sms_port_label)
        sms_port_layout.addWidget(sms_port_edit)
        layout.addLayout(sms_port_layout)
        # 升级服务端口输入
        upgrade_port_layout = QHBoxLayout()
        upgrade_port_label = QLabel("升级服务端口:")
        micro_default_upgrade_port = get_app_config_value('micro_default_upgrade_port', None)
        upgrade_port_edit = QLineEdit()
        upgrade_port_edit.setText(str(self._micro_service_upgrade_port) if hasattr(self,
                                                                                   '_micro_service_upgrade_port') else micro_default_upgrade_port or '')
        upgrade_port_layout.addWidget(upgrade_port_label)
        upgrade_port_layout.addWidget(upgrade_port_edit)
        layout.addLayout(upgrade_port_layout)
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._micro_service_ip = ip_edit.text().strip()
            self._micro_service_sms_port = sms_port_edit.text().strip()
            self._micro_service_upgrade_port = upgrade_port_edit.text().strip()
            if not self._micro_service_ip or not self._micro_service_sms_port or not self._micro_service_upgrade_port:
                QMessageBox.warning(self, "提示", "请填写微服务的IP、短信服务端口和升级服务端口后再保存！")
                return
            self._micro_service_api_url = f"http://{self._micro_service_ip}:{self._micro_service_sms_port}"
            os.environ['PLAYWRIGHT_SERVER_URL'] = self._micro_service_api_url
            # 保存到app.config
            set_app_config_value('micro_default_ip', self._micro_service_ip)
            set_app_config_value('micro_default_sms_port', self._micro_service_sms_port)
            set_app_config_value('micro_default_upgrade_port', self._micro_service_upgrade_port)
            QMessageBox.information(self, "提示",
                                    f"微服务配置已保存:\nIP: {self._micro_service_ip}\n短信服务端口: {self._micro_service_sms_port}\n升级服务端口: {self._micro_service_upgrade_port}")

    def check_and_show_guide_overlay(self):
        """首次运行检测并显示多步骤引导蒙层"""
        from pos_tool_new.utils.app_config_utils import get_app_config_value
        guide_shown = get_app_config_value('guide_shown', 'false')
        if guide_shown != 'true':
            # 获取目标控件
            menu_ip = None
            menu_layout = None
            menu_update = None
            tabbar = None
            splitter_handle = None
            menubar = self.menuBar()
            # 菜单栏“设置”下的各action
            for act in menubar.actions():
                if act.text().startswith("设置"):
                    for sub in act.menu().actions():
                        if "全局IP" in sub.text():
                            menu_ip = sub
                        if "布局" in sub.text():
                            menu_layout = sub
                if act.text().startswith("关于"):
                    for sub in act.menu().actions():
                        if "检查更新" in sub.text():
                            menu_update = sub
            # tab栏
            if hasattr(self, 'tabs'):
                tabbar = self.tabs.tabBar()
            # 分割条handle
            if hasattr(self, 'splitter'):
                splitter_handle = self.splitter.handle(1)
            steps = [
                (menubar, "1. 在‘关于-检查更新’可以检测并升级工具版本。"),
                (menubar, "2. 在‘设置-全局IP’可以设置每个Tab的需要的IP。"),
                (menubar, "3. 在‘设置-布局’可以自定义Tab显示。"),
                (menubar, "4. 在‘设置-临时war包清理’可以删除所有临时war包。"),
                (tabbar, "5. 拖动Tab可以实现Tab自定义排序。"),
                (splitter_handle, "6. 点击日志区分割条的三个点可以折叠/收起日志区。")
            ]
            self.guide_overlay = GuideOverlay(self, steps)
            self.guide_overlay.setGeometry(0, 0, self.width(), self.height())
            self.guide_overlay.setVisible(True)
            self.guide_overlay.raise_()
            self.installEventFilter(self)

    def resizeEvent(self, event):
        if hasattr(self, 'guide_overlay') and self.guide_overlay and self.guide_overlay.isVisible():
            self.guide_overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def clear_history_war_folders(self):
        from pos_tool_new.work_threads import ClearHistoryWarFoldersThread
        def scan_temp_war_dirs():
            temp_dir = tempfile.gettempdir()
            war_dirs = []
            for name in os.listdir(temp_dir):
                path = os.path.join(temp_dir, name)
                if os.path.isdir(path) and name.startswith('war_download'):
                    war_dirs.append(path)
            return war_dirs

        def show_confirm_dialog(war_dirs):
            if not war_dirs:
                QMessageBox.information(self, "临时war包清理", "未发现可清理的临时war包文件夹。")
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("确认临时war包清理")
            dialog.setMinimumWidth(500)
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel(f"将要删除以下{len(war_dirs)}个文件夹："))
            list_widget = QListWidget()
            for d in war_dirs:
                list_widget.addItem(d)
            layout.addWidget(list_widget)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            layout.addWidget(buttons)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 启动后台线程清理
                self.clear_war_thread = ClearHistoryWarFoldersThread()
                def on_result(removed, error_msg):
                    msg = f"已清理 {len(removed)} 个临时war包文件夹。" if removed else "未能删除任何文件夹。"
                    if removed:
                        msg += "\n" + "\n".join(removed)
                    if error_msg:
                        msg += f"\n\n错误信息:\n{error_msg}"
                    QMessageBox.information(self, "清理完成", msg)
                self.clear_war_thread.result_signal.connect(on_result)
                self.clear_war_thread.start()
        # 主线程扫描并弹窗
        war_dirs = scan_temp_war_dirs()
        show_confirm_dialog(war_dirs)

    def _close_marquee_bar(self):
        self.marquee_widget.setVisible(False)
        self.marquee_timer.stop()
        self.marquee_closed_by_user = True

    def _get_display_len(self):
        # 动态计算marquee_bar可显示的字符数
        font_metrics = self.marquee_bar.fontMetrics()
        bar_width = self.marquee_bar.width()
        # 取一个宽字符的宽度，防止中英文混排导致溢出
        char_width = font_metrics.horizontalAdvance('W')
        display_len = max(1, bar_width // char_width)
        return int(display_len * 2.2)

    def _scroll_marquee(self):
        """真正的滚动：文本从右向左移动（彻底修正方向）"""
        if not self.marquee_text:
            self.marquee_bar.setText("")
            return

        display_len = self._get_display_len()
        scroll_text =  self.marquee_text  # 两边都补空格

        # 初始化 scroll_position
        if not hasattr(self, "scroll_position") or self.scroll_position is None:
            self.scroll_position = len(scroll_text) - display_len

        start_pos = self.scroll_position
        end_pos = start_pos + display_len
        show_text = scroll_text[start_pos:end_pos]
        self.marquee_bar.setText(show_text)

        # 向左移动
        self.scroll_position -= 1
        if self.scroll_position < 0:
            self.scroll_position = len(scroll_text) - display_len

    def update_marquee_message(self, msg: str):
        print(f"[Marquee] update_marquee_message called, msg='{msg}'")
        global_log_manager.log(f"[Marquee] update_marquee_message called, msg='{msg}'", "debug")
        if not msg:
            self.marquee_widget.setVisible(False)
            self.marquee_timer.stop()
            print('[Marquee] marquee_timer stopped (empty msg)')
            global_log_manager.log('[Marquee] marquee_timer stopped (empty msg)', 'debug')
            self.marquee_closed_by_user = False
            return
        display_len = self._get_display_len()
        # 循环拼接，保证长度大于等于2倍display_len
        base_text = msg + (" " * display_len)
        while len(base_text) < 2 * display_len:
            base_text += msg + (" " * display_len)
        self.marquee_text = base_text
        self.scroll_position = 0  # 从最左侧开始
        self.marquee_widget.setVisible(True)
        self.marquee_closed_by_user = False
        self._scroll_marquee()
        self.marquee_timer.start(120)
        print('[Marquee] marquee_timer started')
        global_log_manager.log('[Marquee] marquee_timer started', 'debug')


def create_main_window():
    """创建主窗口"""
    start_time = time.time()
    win = MainWindow()
    end_time = time.time()

    cost_ms = int((end_time - start_time) * 1000)
    global_log_manager.log(f"应用启动耗时: {cost_ms} ms", "info")

    return win


if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = ModernSplashScreen(resource_path('UI/loading.gif'), duration=1800)
    splash.start(create_main_window)
    sys.exit(app.exec())

