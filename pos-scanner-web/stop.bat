@echo off
chcp 65001 >nul
title POS Scanner Web - 停止服务

echo ========================================
echo   POS Scanner Web - 停止服务
echo ========================================
echo.

echo [停止] 正在停止后端服务 (Python)...
taskkill /f /im python.exe 2>nul
if errorlevel 1 (
    echo [信息] 未找到运行中的 Python 进程
) else (
    echo [完成] 后端服务已停止
)

echo [停止] 正在停止前端服务 (Node)...
taskkill /f /im node.exe 2>nul
if errorlevel 1 (
    echo [信息] 未找到运行中的 Node 进程
) else (
    echo [完成] 前端服务已停止
)

echo.
echo 所有服务已停止
pause
