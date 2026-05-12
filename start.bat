@echo off
chcp 65001 > nul
title AutoCopilot 工业视觉检测 Agent
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║        AutoCopilot 工业视觉检测 Agent v1.0                ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

:: 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
pip show requests >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install requests python-dotenv pyinstaller -q
)

:: 创建配置目录
if not exist "config" mkdir config
if not exist "logs" mkdir logs

:: 检查配置文件
if not exist ".env" (
    echo [提示] 首次运行，创建配置文件...
    (
        echo # AutoCopilot Agent 配置
        echo LOCAL_MODE=true
        echo MIMO_API_KEY=tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc
        echo MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
        echo MIMO_MODEL=mimo-v2.5
    ) > .env
    echo [完成] 请编辑 .env 文件配置您的API密钥
)

echo.
echo 启动中，请稍候...
echo.

:: 启动程序
python -c "from deploy.autocopilot_client import *; interactive_mode(AutoCopilotClient())"

pause
