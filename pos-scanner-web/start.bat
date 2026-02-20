@echo off
chcp 65001 >nul
title POS Scanner Web - 本地启动

echo ========================================
echo   POS Scanner Web - 本地启动脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

echo [启动] 后端服务...
cd /d "%~dp0backend"
start "Backend - Flask" cmd /k "python app.py"

echo [等待] 等待后端启动...
timeout /t 3 /nobreak >nul

echo [启动] 前端服务...
cd /d "%~dp0frontend"
start "Frontend - Vite" cmd /k "npm run dev"

echo.
echo ========================================
echo   服务已启动！
echo   后端: http://localhost:5000
echo   前端: http://localhost:3000
echo ========================================
echo.
echo 按任意键打开浏览器...
pause >nul

start http://localhost:3000
