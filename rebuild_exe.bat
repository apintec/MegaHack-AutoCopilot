@echo off
echo ========================================
echo AutoCopilot.exe 重组脚本
echo ========================================
echo.

REM 检查base64文件
if not exist "AutoCopilot.exe.b64" (
    echo 错误: 找不到 AutoCopilot.exe.b64 文件！
    echo 请确保已下载所有文件碎片。
    pause
    exit /b 1
)

REM 解码base64
echo 正在重组exe文件...
certutil -decode AutoCopilot.exe.b64 AutoCopilot.exe

if exist "AutoCopilot.exe" (
    echo.
    echo ========================================
    echo 重组成功！
    echo exe文件: AutoCopilot.exe
    echo ========================================
) else (
    echo.
    echo 错误: 重组失败！
    pause
    exit /b 1
)

REM 清理临时文件
del AutoCopilot.exe.b64

echo.
echo 现在可以运行: AutoCopilot.exe
pause
