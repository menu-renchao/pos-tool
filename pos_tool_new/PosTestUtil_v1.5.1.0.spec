# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main2.py'],
    pathex=['D:\menusifu\PythonProject\rc\pos_tool_new'],
    binaries=[],
    datas=[('UI/app.ico', 'UI'),('UI/loading.gif', 'UI'), ('version_info/version_info.html', 'version_info')],
    hiddenimports=[
        'pos_tool_new.sms.sms_window',
        'pos_tool_new.sms.sms_service',
        'pos_tool_new.work_threads',
        'pos_tool_new.backend',
        'pos_tool_new.version_info.version_info',
        'pos_tool_new.utils.log_manager',
        'pos_tool_new.linux_pos.linux_window',
        'pos_tool_new.linux_file_config.file_config_linux_window',
        'pos_tool_new.windows_pos.windows_window',
        'pos_tool_new.windows_file_config.file_config_win_window',
        'pos_tool_new.db_config.db_config_window',
        'pos_tool_new.scan_pos.scan_pos_window',
        'pos_tool_new.caller_id.caller_window',
        'pos_tool_new.license_backup.license_window',
        'pos_tool_new.download_war.download_war_window',
        'pos_tool_new.generate_img.generate_img_window',
        'pos_tool_new.random_mail.random_mail_window',
        # 其它 tab 相关模块可按需补全
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PosTestUtil_v1.5.1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['UI\\app.ico'],
)
