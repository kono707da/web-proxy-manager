@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo   Proxy Manager - Startup Script
echo ========================================
echo.

REM Check Python (prefer venv)
set PYTHON=python
if exist "%~dp0backend\venv\Scripts\python.exe" (
    set PYTHON=%~dp0backend\venv\Scripts\python.exe
)

REM Check port occupation
powershell -ExecutionPolicy Bypass -File "%~dp0kill_stale_port.ps1"
if %ERRORLEVEL% equ 2 (
    echo [ERROR] Port 8000 is occupied by another program. Please release the port or change port in config.yaml
    pause
    exit /b 1
)

REM Check frontend build
if not exist "%~dp0frontend\dist\index.html" (
    echo [BUILD] Frontend build not found, building...
    where npm >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] npm not found, please install Node.js 16+
        pause
        exit /b 1
    )
    pushd "%~dp0frontend"
    call npm install
    call npm run build
    popd
)

REM Add project bundled mihomo binary to PATH (local dev only, backend\bin\mihomo.exe)
if exist "%~dp0backend\bin\mihomo.exe" (
    set PATH=%~dp0backend\bin;!PATH!
)

REM Check mihomo
where mihomo >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARN] mihomo not found, proxy core features will be unavailable
    echo        Docker deployment includes mihomo, local dev needs manual install
    echo.
)

REM Start backend
echo [START] Proxy Manager (port 8000)
cd /d "%~dp0backend"
%PYTHON% run.py
pause
