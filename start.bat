@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo ========================================
echo   Proxy Manager - 启动脚本
echo ========================================
echo.

REM 检查 Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 Python，请安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查端口占用（本应用占用则杀掉重启，他人占用则提示）
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

REM 检查 mihomo 二进制（本地开发需要，Docker 部署无需）
where mihomo >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [警告] 未找到 mihomo 二进制，内核管理功能将不可用
    echo        本地开发请从 https://github.com/MetaCubeX/mihomo/releases 下载
    echo        并放入 PATH 或在 backend/config.yaml 的 mihomo.binary 填写绝对路径
    echo        Docker 部署无需手动安装，镜像内已内置
    echo.
)

REM 启动后端（前后端合并到 8000 端口）
echo [启动] Proxy Manager (端口 8000)
cd /d "%~dp0backend"
python run.py
pause
