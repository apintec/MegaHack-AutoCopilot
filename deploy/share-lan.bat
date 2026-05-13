@echo off
chcp 65001 > nul
title AutoCopilot - 局域网共享

echo.
echo ============================================================
echo    AutoCopilot 工业视觉检测专家 - 局域网共享模式
echo ============================================================
echo.
echo  正在检测本机 IP 地址 ...
echo.
echo  请把下面任意一条链接发给 "和你同一个 Wi-Fi / 局域网" 的同事：
echo ------------------------------------------------------------

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4"') do (
    setlocal enabledelayedexpansion
    set "ip=%%a"
    set "ip=!ip: =!"
    echo    http://!ip!:8080
    endlocal
)

echo ------------------------------------------------------------
echo.
echo  注意事项：
echo   1. 别人必须和你在同一个 Wi-Fi / 局域网内才能打开
echo   2. 首次启动 Windows 会弹防火墙提示，请选 "允许访问"
echo   3. 当前 API Key 是硬编码的，分享出去等于让别人共用你的额度
echo   4. 关闭此窗口或按 Ctrl+C 即可停止服务
echo.
echo ============================================================
echo.

cd /d "%~dp0\.."
python deploy\app.py

pause
