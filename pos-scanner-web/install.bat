@echo off
chcp 65001 >nul
title POS Scanner Web - 安装依赖

echo ========================================
echo   POS Scanner Web - 安装依赖
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

echo [提示] 如果使用代理，请确保代理支持 HTTPS
echo.

echo [安装] 后端依赖...
cd /d "%~dp0backend"

:: 方案1: 使用清华镜像
echo 尝试使用清华镜像...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if not errorlevel 1 goto backend_done

echo.
echo [重试] 清华镜像失败，尝试阿里云镜像...
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
if not errorlevel 1 goto backend_done

echo.
echo [重试] 阿里云镜像失败，尝试官方源(信任证书)...
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
if not errorlevel 1 goto backend_done

echo [错误] 后端依赖安装失败，请检查网络或手动安装
pause
exit /b 1

:backend_done
echo [完成] 后端依赖安装成功

echo.
echo [安装] 前端依赖...
cd /d "%~dp0frontend"

echo 尝试使用淘宝镜像...
npm install --registry=https://registry.npmmirror.com
if not errorlevel 1 goto frontend_done

echo [重试] 淘宝镜像失败，尝试官方源...
npm install
if not errorlevel 1 goto frontend_done

echo [错误] 前端依赖安装失败
pause
exit /b 1

:frontend_done
echo [完成] 前端依赖安装成功

echo.
echo ========================================
echo   所有依赖安装完成！
echo   请运行 start.bat 启动服务
echo ========================================
pause
