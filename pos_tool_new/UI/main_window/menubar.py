"""
主窗口菜单栏模块
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout, QLabel, QDialog, QCheckBox, QLineEdit

from pos_tool_new.update_dialog import check_and_update_exe
from pos_tool_new.utils.app_config_utils import (
    load_tab_config_from_app, save_tab_config_to_app,
    get_app_config_value, set_app_config_value,
    TAB_ID_MAP, TAB_ID_LIST
)


def setup_menubar(window, menubar):
    """设置菜单栏"""
    # 添加关于菜单
    about_menu = menubar.addMenu("关于(&A)")
    # 添加"检查更新"菜单项
    check_update_action = QAction("检查更新", window)
    check_update_action.triggered.connect(lambda: check_and_update_exe(window))
    about_menu.addAction(check_update_action)

    version_action = QAction("版本信息", window)
    version_action.triggered.connect(lambda: window.show_version_info())
    about_menu.addAction(version_action)

    # 添加设置菜单
    settings_menu = menubar.addMenu("设置(&S)")
    global_ip_action = QAction("全局IP", window)
    global_ip_action.triggered.connect(lambda: show_global_ip_dialog(window))
    settings_menu.addAction(global_ip_action)

    micro_service_action = QAction("微服务", window)
    micro_service_action.triggered.connect(lambda: show_micro_service_config_dialog(window))
    settings_menu.addAction(micro_service_action)

    layout_action = QAction("布局", window)
    layout_action.triggered.connect(lambda: show_layout_config_dialog(window))
    settings_menu.addAction(layout_action)

    # 添加清空历史war包菜单项
    clear_war_action = QAction("临时war包清理", window)
    clear_war_action.triggered.connect(lambda: clear_history_war_folders(window))
    settings_menu.addAction(clear_war_action)

    tc_session_action = QAction("TCSESSIONID配置", window)
    tc_session_action.triggered.connect(lambda: show_tc_session_config_dialog(window))
    settings_menu.addAction(tc_session_action)

    window.setMenuBar(menubar)


def show_global_ip_dialog(window):
    """弹出全局IP配置窗口（QComboBox方式）"""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel
    dialog = QDialog(window)
    dialog.setWindowTitle("配置全局IP")
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("请输入全局IP:"))
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItems([
        "192.168.0.", "192.168.1.", "10.24.1.",
        "10.1.10.", "10.0.10.", "192.168.252.", "192.168.253."
    ])
    current_ip = window.get_global_ip()
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
            window.set_global_ip(ip)
            # 同步所有FileConfigTabWidget的host_ip
            for i in range(window.tabs.count()):
                tab = window.tabs.widget(i)
                if hasattr(tab, 'set_host_ip') and callable(tab.set_host_ip):
                    tab.set_host_ip(ip)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(window, "提示",
                                    f"全局IP已设置为: {ip}。仅首次会同步到所有选项卡，之后各选项卡可单独修改IP。")


def show_micro_service_config_dialog(window):
    """显示微服务配置对话框"""
    dialog = QDialog(window)
    dialog.setWindowTitle("微服务配置")
    layout = QVBoxLayout(dialog)
    # IP输入
    ip_layout = QVBoxLayout(dialog)
    ip_label = QLabel("服务IP:")
    micro_default_ip = get_app_config_value('micro_default_ip', None)
    ip_edit = QLineEdit()
    ip_edit.setText(window._micro_service_ip if hasattr(window, '_micro_service_ip') else micro_default_ip or '')
    ip_layout.addWidget(ip_label)
    ip_layout.addWidget(ip_edit)
    layout.addLayout(ip_layout)
    # 微服务端口输入（合并短信和升级服务端口）
    port_layout = QVBoxLayout(dialog)
    port_label = QLabel("微服务端口:")
    micro_default_port = get_app_config_value('micro_default_port', None)
    port_edit = QLineEdit()
    port_edit.setText(
        str(window._micro_service_port) if hasattr(window, '_micro_service_port') else micro_default_port or '')
    port_layout.addWidget(port_label)
    port_layout.addWidget(port_edit)
    layout.addLayout(port_layout)
    # 按钮
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(buttons)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        window._micro_service_ip = ip_edit.text().strip()
        window._micro_service_port = port_edit.text().strip()
        if not window._micro_service_ip or not window._micro_service_port:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(window, "提示", "请填写微服务的IP和端口后再保存！")
            return
        window._micro_service_api_url = f"http://{window._micro_service_ip}:{window._micro_service_port}"
        import os
        os.environ['PLAYWRIGHT_SERVER_URL'] = window._micro_service_api_url
        # 保存到app.config
        set_app_config_value('micro_default_ip', window._micro_service_ip)
        set_app_config_value('micro_default_port', window._micro_service_port)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(window, "提示",
                                f"微服务配置已保存:\nIP: {window._micro_service_ip}\n端口: {window._micro_service_port}")


def show_layout_config_dialog(window):
    """显示布局配置对话框"""
    dialog = QDialog(window)
    dialog.setWindowTitle("布局 - 选择常用Tab")
    layout = QVBoxLayout(dialog)
    config = load_tab_config_from_app()
    tabs_enabled = config.get("tabs", {tid: True for tid in TAB_ID_LIST})
    checkboxes = {}

    # 全选复选框
    select_all_cb = QCheckBox("全选")
    layout.addWidget(select_all_cb)

    # 防止递归更新的标志
    window._updating_checkboxes = False

    def update_select_all_state():
        """更新全选复选框的状态"""
        if window._updating_checkboxes:
            return

        window._updating_checkboxes = True

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

        window._updating_checkboxes = False

    def on_select_all_changed(state):
        """全选复选框状态改变时的处理"""
        if window._updating_checkboxes:
            return
        window._updating_checkboxes = True
        if state in [1, 2]:  # Checked
            for cb in checkboxes.values():
                cb.setChecked(True)
        elif state == 0:  # Unchecked
            for cb in checkboxes.values():
                cb.setChecked(False)
        # 部分选中状态不需要处理，因为用户不能直接设置部分选中

        window._updating_checkboxes = False
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
        window.refresh_tabs()


def show_tc_session_config_dialog(window):
    """显示TCSESSIONID配置对话框"""
    from pos_tool_new.utils.app_config_utils import get_cookie_and_sessionid, set_cookie_and_sessionid
    dialog = QDialog(window)
    dialog.setWindowTitle("TCSESSIONID配置")
    dialog.setFixedWidth(500)
    layout = QVBoxLayout(dialog)
    ids = get_cookie_and_sessionid()
    label1 = QLabel("COOKIE:")
    edit1 = QLineEdit()
    edit1.setText(ids["COOKIE"])
    label2 = QLabel("TCSESSIONID:")
    edit2 = QLineEdit()
    edit2.setText(ids["TCSESSIONID"])
    layout.addWidget(label1)
    layout.addWidget(edit1)
    layout.addWidget(label2)
    layout.addWidget(edit2)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(buttons)

    def on_ok():
        set_cookie_and_sessionid(edit1.text().strip(), edit2.text().strip())
        dialog.accept()

    buttons.accepted.connect(on_ok)
    buttons.rejected.connect(dialog.reject)
    dialog.exec()


def clear_history_war_folders(window):
    """清理历史war包文件夹"""
    from pos_tool_new.work_threads import ClearHistoryWarFoldersThread
    import tempfile
    import os

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
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(window, "临时war包清理", "未发现可清理的临时war包文件夹。")
            return
        from PyQt6.QtWidgets import QMessageBox, QListWidget
        dialog = QDialog(window)
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
            window.clear_war_thread = ClearHistoryWarFoldersThread()

            def on_result(removed, error_msg):
                msg = f"已清理 {len(removed)} 个临时war包文件夹。" if removed else "未能删除任何文件夹。"
                if removed:
                    msg += "\n" + "\n".join(removed)
                if error_msg:
                    msg += f"\n\n错误信息:\n{error_msg}"
                QMessageBox.information(window, "清理完成", msg)

            window.clear_war_thread.result_signal.connect(on_result)
            window.clear_war_thread.start()

    # 主线程扫描并弹窗
    war_dirs = scan_temp_war_dirs()
    show_confirm_dialog(war_dirs)
