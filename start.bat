@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo   Proxy Manager - 启动脚本
echo ========================================
echo.

REM 检查 Python（优先使用 venv）
set PYTHON=python
if exist "%~dp0backend\venv\Scripts\python.exe" (
    set PYTHON=%~dp0backend\venv\Scripts\python.exe
)

REM 检查端口占用
powershell -ExecutionPolicy Bypass -File "%~dp0kill_stale_port.ps1"
if %ERRORLEVEL% equ 2 (
    echo [错误] 端口 8000 被其他程序占用，请先释放该端口或修改 config.yaml 中的 port
    pause
    exit /b 1
)

REM 检查前端构建产物
if not exist "%~dp0frontend\dist\index.html" (
    echo [构建] 前端构建产物不存在，开始构建...
    where npm >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [错误] 未找到 npm，请安装 Node.js 16+
        pause
        exit /b 1
    )
    pushd "%~dp0frontend"
    call npm install
    call npm run build
    popd
)

REM 将项目自带的 mihomo 二进制目录加入 PATH（本地开发用，backend\bin\mihomo.exe）
if exist "%~dp0backend\bin\mihomo.exe" (
    set PATH=%~dp0backend\bin;!PATH!
)

REM 检查 mihomo
where mihomo >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [警告] 未找到 mihomo，内核管理功能将不可用
    echo        Docker 部署无需手动安装，镜像内已内置
    echo.
)

REM 启动后端
echo [启动] Proxy Manager (端口 8000)
cd /d "%~dp0backend"
%PYTHON% run.py
pause