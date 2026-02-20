@echo off
chcp 65001 >nul

echo ========================================
echo   添加防火墙规则
echo ========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [错误] 请以管理员身份运行此脚本
    echo 右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo [添加] 后端端口 5000...
netsh advfirewall firewall add rule name="POS Scanner Backend" dir=in action=allow protocol=tcp localport=5000

echo [添加] 前端端口 3000...
netsh advfirewall firewall add rule name="POS Scanner Frontend" dir=in action=allow protocol=tcp localport=3000

echo.
echo ========================================
echo   防火墙规则添加完成！
echo   局域网可通过本机IP访问
echo ========================================
pause
