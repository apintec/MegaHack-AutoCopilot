@echo off
chcp 65001 > nul
title AutoCopilot - 公网临时分享 (Cloudflare Tunnel)

echo.
echo ============================================================
echo    AutoCopilot 工业视觉检测专家 - 公网临时链接
echo ============================================================
echo.
echo  本脚本会做 3 件事：
echo    1) 检查并自动下载 cloudflared.exe (约 20 MB, 一次性)
echo    2) 后台启动 Web 服务 (localhost:8080)
echo    3) 创建 Cloudflare 临时隧道, 给一条 https 公网链接
echo.
echo  注意：当前 API Key 硬编码在代码里，公网链接发给谁，
echo        谁都能用你的 mimo 额度。仅作短期演示，请勿长期暴露。
echo.
echo ============================================================
echo.

cd /d "%~dp0\.."

set CFD_DIR=deploy\bin
set CFD_EXE=%CFD_DIR%\cloudflared.exe

if not exist "%CFD_EXE%" (
    echo [1/3] 首次运行，下载 cloudflared.exe ...
    if not exist "%CFD_DIR%" mkdir "%CFD_DIR%"
    powershell -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CFD_EXE%' -UseBasicParsing"
    if not exist "%CFD_EXE%" (
        echo.
        echo [X] 下载失败。请手动从下面地址下载 cloudflared-windows-amd64.exe，
        echo     重命名为 cloudflared.exe 后放到目录: %CD%\%CFD_DIR%\
        echo     https://github.com/cloudflare/cloudflared/releases/latest
        echo.
        pause
        exit /b 1
    )
    echo     OK
) else (
    echo [1/3] cloudflared.exe 已存在
)

echo.
echo [2/3] 后台启动 Web 服务 ...
start "AutoCopilot-Web" /MIN cmd /c "python deploy\app.py"
timeout /t 4 /nobreak >nul
echo     OK (窗口已最小化, 标题: AutoCopilot-Web)

echo.
echo [3/3] 启动 Cloudflare 临时隧道 ...
echo.
echo ============================================================
echo  请在下方 cloudflared 的输出里找形如
echo      https://xxxx-xxxx-xxxx.trycloudflare.com
echo  的那条链接, 发给任何人 (浏览器直接打开即可使用)。
echo  关闭此窗口或按 Ctrl+C 即停止公网访问。
echo  (注意: 后台 Web 进程会一起被脚本结束)
echo ============================================================
echo.

"%CFD_EXE%" tunnel --url http://localhost:8080 --no-autoupdate

echo.
echo 清理后台 Web 进程 ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo 已退出。
pause
