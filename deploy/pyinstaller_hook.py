# AutoCopilot 客户端打包配置

# PyInstaller打包命令:
# pip install pyinstaller python-dotenv
# pyinstaller --onefile --name AutoCopilot --icon=icon.ico --add-data "src;src" deploy/autocopilot_client.py

import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
hiddenimports = [
    'requests',
    'dotenv',
    'json',
    'urllib3',
    'charset_normalizer',
    'certifi',
    'idna',
]

# Windows 特定补丁：交互式控制台依赖
if sys.platform == 'win32':
    hiddenimports += [
        'pyreadline3',
        'colorama',
    ]
