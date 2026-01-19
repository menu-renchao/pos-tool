"""
主窗口类
"""
import os
import sys

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFont, QPalette, QIcon, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget,
    QMainWindow,
    QMenuBar, QVBoxLayout
)

from pos_tool_new.UI.main_window.log_area import create_log_area
from pos_tool_new.UI.main_window.menubar import setup_menubar
from pos_tool_new.UI.main_window.progress_manager import ProgressManager
from pos_tool_new.UI.main_window.tab_manager import create_tab_contents, refresh_tabs, on_tab_moved
from pos_tool_new.UI.styles import (
    get_stylesheet, get_splitter_style
)
from pos_tool_new.UI.widgets import (
    CustomSplitter, GuideOverlay
)
from pos_tool_new.backend import Backend
from pos_tool_new.marquee import MarqueeBar
from pos_tool_new.utils.app_config_utils import (
    get_app_config_value
)
from pos_tool_new.utils.log_manager import global_log_manager
from pos_tool_new.version_info.version_info import VersionInfoDialog


def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，支持PyInstaller打包后的路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        self._sms_service_ip = get_app_config_value('micro_default_ip', None)
        self._sms_service_port = get_app_config_value('micro_default_port', None)
        super().__init__()

        # 初始化短信微服务环境变量，首次启动即生效
        if self._sms_service_ip and self._sms_service_port:
            default_url = f"http://{self._sms_service_ip}:{self._sms_service_port}"
            os.environ['PLAYWRIGHT_SERVER_URL'] = default_url
        else:
            os.environ['PLAYWRIGHT_SERVER_URL'] = ''

        self.marquee_widget = MarqueeBar(self)

        # 初始化进度管理器
        self.progress_manager = ProgressManager(self)
        self.progress_manager.setup_progress_components()

        self._init_components()
        self.setup_backend()
        self.setup_ui()

        global_log_manager.log_received.connect(self.log_text.append_colored_text)

        # 首次运行检测
        self.guide_overlay = None
        self.check_and_show_guide_overlay()
        self.check_and_clear_history_exe()

    def check_and_clear_history_exe(self):
        """检查并清理历史exe文件"""
        from pos_tool_new.utils.app_config_utils import get_app_config_value, set_app_config_value
        import os
        if get_app_config_value('need_clear_history_files', 'false') == 'true':
            # 删除旧exe
            old_exe_path = get_app_config_value('old_exe_path', '')
            if old_exe_path and os.path.exists(old_exe_path):
                try:
                    os.remove(old_exe_path)
                except Exception:
                    pass  # 可加日志
                set_app_config_value('old_exe_path', '')
            set_app_config_value('need_clear_history_files', 'false')

    def _init_components(self):
        """初始化组件"""
        self.progress_manager.setup_progress_timer()

    def setup_ui(self):
        """设置UI界面"""
        self._setup_window_properties()
        self.setup_styles()
        self.create_menubar()

        central_widget = self._create_central_widget()

        # 在主布局顶部插入跑马灯浮层条
        layout = central_widget.layout() or central_widget.findChild(QVBoxLayout)
        if layout is not None:
            if hasattr(layout, 'insertWidget'):
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
        handle = self.splitter.handle(1)
        handle.installEventFilter(self)
        self._log_collapsed = False
        self._log_last_size = 180

        # 分割条样式
        self.splitter.setStyleSheet(get_splitter_style())

    def eventFilter(self, obj, event):
        """事件过滤器"""
        # 分割条handle收起/展开日志区
        if hasattr(self, 'splitter') and obj == self.splitter.handle(1):
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
        self.setWindowTitle("POS测试工具 v1.5.1.7 by Mansuper")
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
        self.tabs.tabBar().tabMoved.connect(lambda: on_tab_moved(self))

        # 创建日志区域
        self.log_group, self.log_text = create_log_area(self)

        # 使用自定义分割器
        self.splitter = CustomSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.log_group)
        self.log_group.setMinimumHeight(270)
        self.splitter.setSizes([600, 180])
        main_layout.addWidget(self.splitter)

        # 添加底部部件
        main_layout.addWidget(self.progress_manager.create_bottom_widget())

        # 创建选项卡内容
        create_tab_contents(self)

        return central_widget

    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar() or QMenuBar(self)
        setup_menubar(self, menubar)

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
        app_instance = QApplication.instance()
        if app_instance is not None:
            app_instance.setStyle("Fusion")

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

            app_instance.setPalette(palette)
            app_instance.setFont(QFont("Microsoft YaHei", 9))

        self.setStyleSheet(get_stylesheet())

    def clear_logs(self):
        """清除日志"""
        if self.log_text:
            self.log_text.clear()

    def append_log(self, msg, level="info"):
        """添加日志"""
        global_log_manager.log(msg, level)

    def get_global_ip(self) -> str:
        """读取全局IP（仅内存，不写文件）"""
        return getattr(self, '_global_ip', '')

    def set_global_ip(self, ip: str):
        """保存全局IP（仅内存，不写文件）"""
        self._global_ip = ip

    def load_layout_config(self):
        """加载布局配置"""
        from pos_tool_new.utils.app_config_utils import get_app_config_value
        layout_config = {}
        from pos_tool_new.UI.main_window.tab_manager import get_tab_imports
        tab_names = [tab_name for _, _, tab_name in get_tab_imports()]
        for tab_name in tab_names:
            value = get_app_config_value(tab_name, None)
            if value is not None:
                layout_config[tab_name] = (value.lower() == 'true')
            else:
                layout_config[tab_name] = True
        return layout_config

    def refresh_tabs(self):
        """刷新选项卡"""
        refresh_tabs(self)

    def check_and_show_guide_overlay(self):
        """首次运行检测并显示多步骤引导蒙层"""
        from pos_tool_new.utils.app_config_utils import get_app_config_value
        guide_shown = get_app_config_value('guide_shown', 'false')
        if guide_shown != 'true':
            # 获取目标控件
            menubar = self.menuBar()
            # tab栏
            if hasattr(self, 'tabs'):
                tabbar = self.tabs.tabBar()
            else:
                tabbar = None
            # 分割条handle
            if hasattr(self, 'splitter'):
                splitter_handle = self.splitter.handle(1)
            else:
                splitter_handle = None
            steps = [
                (menubar, "1. 在'关于-检查更新'可以检测并升级工具版本。"),
                (menubar, "2. 在'设置-全局IP'可以设置每个Tab的需要的IP。"),
                (menubar, "3. 在'设置-布局'可以自定义Tab显示。"),
                (menubar, "4. 在'设置-临时war包清理'可以删除所有临时war包。"),
                (tabbar, "5. 拖动Tab可以实现Tab自定义排序。"),
                (splitter_handle, "6. 点击日志区分割条的三个点可以折叠/收起日志区。")
            ]
            self.guide_overlay = GuideOverlay(self, steps)
            self.guide_overlay.setGeometry(0, 0, self.width(), self.height())
            self.guide_overlay.setVisible(True)
            self.guide_overlay.raise_()
            self.installEventFilter(self)

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        if hasattr(self, 'guide_overlay') and self.guide_overlay and self.guide_overlay.isVisible():
            self.guide_overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def update_marquee_message(self, msg: str):
        """更新跑马灯消息"""
        self.marquee_widget.update_marquee_message(msg)

    def setup_progress_animation(self, interval: int):
        """设置进度条动画"""
        self.progress_manager.setup_progress_animation(interval)

    def on_restart_finished(self):
        """重启完成处理"""
        self.progress_manager.on_restart_finished()

    def show_upload_speed(self, speed_text):
        """显示上传速度"""
        self.progress_manager.show_upload_speed(speed_text)

    def hide_upload_speed(self):
        """隐藏上传速度"""
        self.progress_manager.hide_upload_speed()

    @property
    def progress_bar(self):
        return self.progress_manager.progress_bar

    @property
    def speed_label(self):
        return self.progress_manager.speed_label
