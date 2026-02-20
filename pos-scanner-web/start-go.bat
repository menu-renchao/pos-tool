@echo off
chcp 65001 >nul
title POS Scanner - 前后端服务

echo ========================================
echo   POS Scanner 一键启动 (Go版本)
echo ========================================
echo.

:: 检查 Go 是否安装
where go >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Go 环境，请先安装 Go
    echo 下载地址: https://go.dev/dl/
    pause
    exit /b 1
)

:: 检查 Node 是否安装
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js 环境，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

:: 设置 Go 代理 (国内镜像)
go env -w GOPROXY=https://goproxy.cn,direct >nul 2>&1

:: 启动后端 (新窗口)
echo [1/2] 启动 Go 后端...
start "POS Scanner - Go 后端" /d "%~dp0backend-go" cmd /k go get modernc.org/sqlite@latest ^&^& go mod tidy ^& go run cmd/server/main.go

:: 等待后端启动
timeout /t 2 /nobreak >nul

:: 启动前端 (新窗口)
echo [2/2] 启动 React 前端...
start "POS Scanner - 前端" /d "%~dp0frontend" cmd /k npm run dev

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo   后端地址: http://localhost:5000
echo   前端地址: http://localhost:3000
echo   默认账号: admin / admin123
echo.
echo   关闭此窗口不会停止服务
echo   要停止请关闭对应的命令行窗口
echo ========================================
echo.

pause
