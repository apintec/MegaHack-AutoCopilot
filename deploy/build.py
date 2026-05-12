"""
AutoCopilot Agent 部署脚本
一键打包为独立exe文件
"""

import os
import sys
import subprocess
import shutil

def check_dependencies():
    """检查并安装依赖"""
    print("🔍 检查依赖...")
    
    required = ['pyinstaller', 'python-dotenv', 'requests']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"  ✅ {pkg}")
        except ImportError:
            missing.append(pkg)
            print(f"  ❌ {pkg} (需要安装)")
    
    if missing:
        print(f"\n📦 安装缺失的依赖: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        print("✅ 依赖安装完成")

def build_exe():
    """构建exe文件"""
    print("\n🔨 开始构建exe...")
    
    # PyInstaller命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # 打包成单个文件
        '--name', 'AutoCopilot',        # exe名称
        '--console',                    # 控制台应用
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不询问确认
    ]
    
    # 添加主程序
    cmd.append('deploy/autocopilot_client.py')
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ 构建成功！")
        print(f"📁 exe文件位置: dist/AutoCopilot.exe")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 构建失败: {e}")
        return False
    
    return True

def create_start_script():
    """创建启动脚本"""
    print("\n📝 创建启动脚本...")
    
    # Windows批处理脚本
    bat_content = '''@echo off
chcp 65001 > nul
echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║        AutoCopilot 工业视觉检测 Agent v1.0                ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo 启动中...
echo.
AutoCopilot.exe
pause
'''
    
    with open('start.bat', 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    print("✅ 已创建 start.bat")

def create_env_template():
    """创建环境变量模板"""
    print("\n📝 创建环境配置模板...")
    
    env_content = '''# AutoCopilot Agent 配置

# 运行模式: true=本地模式, false=远程服务模式
LOCAL_MODE=true

# 小米MiMo API配置
MIMO_API_KEY=tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5

# 远程Agent服务地址（可选）
REMOTE_AGENT_URL=https://your-agent-service.coze.cn/api/chat
'''
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 已创建 .env 配置文件模板")

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          AutoCopilot Agent 部署工具 v1.0                      ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # 检查依赖
    check_dependencies()
    
    # 创建配置
    create_env_template()
    
    # 构建exe
    if build_exe():
        create_start_script()
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║                    部署完成！                                ║
╠══════════════════════════════════════════════════════════════╣
║ 使用方法：                                                    ║
║ 1. 双击 start.bat 启动                                       ║
║ 2. 或直接运行 dist/AutoCopilot.exe                          ║
║ 3. 编辑 .env 文件配置API密钥                                ║
╚══════════════════════════════════════════════════════════════╝
        """)

if __name__ == "__main__":
    main()
