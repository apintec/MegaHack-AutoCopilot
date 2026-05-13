# AutoCopilot Agent 部署指南

## 🌐 分享给别人用（最常见）

| 场景 | 一键脚本 | 说明 |
|---|---|---|
| **同一 Wi-Fi 局域网内同事访问** | 双击 `deploy/share-lan.bat` | 自动列出本机 IP，对方浏览器打开 `http://<IP>:8080` 即可，无需额外安装 |
| **任意网络（包括手机 4G）公网访问** | 双击 `deploy/share-public.bat` | 自动下载 cloudflared，给一条 `https://xxx.trycloudflare.com` 临时链接，关掉脚本即失效 |

> ⚠️ **安全提示**：当前 `deploy/app.py` 里 `API_KEY` 是硬编码的。如果用公网分享，等于让任何拿到链接的人共用你的 mimo API 额度，**仅作短期演示用，用完务必关闭脚本**。如需长期共享，请改用环境变量 + 加访问控制。

### 局域网分享步骤

1. 双击 `deploy\share-lan.bat`
2. 终端会列出本机的所有 IPv4 地址（例如 `http://192.168.1.20:8080`）
3. 把对应链接发给同一 Wi-Fi 的同事，浏览器打开即用
4. Windows 首次启动可能弹"防火墙"窗口，选 **"允许访问"**

### 公网分享步骤（无需买服务器、无需备案）

1. 双击 `deploy\share-public.bat`
2. 首次会下载 `cloudflared.exe`（~20 MB，存到 `deploy/bin/`，只下载一次）
3. 等几秒，终端会输出形如：
   ```
   Your quick Tunnel has been created! Visit it at:
   https://lucky-cat-meadow-1234.trycloudflare.com
   ```
4. 把这条 `https://...trycloudflare.com` 链接发出去，**任何人在任何网络都能直接打开**（自带 HTTPS）
5. 关闭脚本窗口 = 公网链接立即失效 + Web 服务停止

---

## 📦 快速开始

### 方法一：一键打包exe (推荐)

```bash
cd deploy
python build.py
```

运行后会自动：
1. 安装所需依赖
2. 打包exe到 `dist/AutoCopilot.exe`
3. 创建启动脚本 `start.bat`

### 方法二：命令行运行

```bash
# 安装依赖
pip install -r deploy/requirements.txt

# 交互式对话
python deploy/autocopilot_client.py

# 快速需求分析
python deploy/autocopilot_client.py --mode analyze

# 生成代码
python deploy/autocopilot_client.py --mode codegen
```

### 方法三：Web界面 (需要额外安装gradio)

```bash
# 安装gradio
pip install gradio

# 启动Web界面
python deploy/web_app.py

# 访问 http://localhost:7860
```

---

## 🔧 详细部署步骤

### 1. 配置API密钥

编辑 `.env` 文件：

```env
# 小米MiMo API配置
MIMO_API_KEY=你的API密钥
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5
```

### 2. 打包为exe (Windows)

```bash
# 安装pyinstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --name AutoCopilot deploy/autocopilot_client.py

# exe位置
dist/AutoCopilot.exe
```

### 3. 部署到服务器 (Linux)

```bash
# 安装依赖
pip install -r requirements.txt

# 使用nohup后台运行
nohup python deploy/web_app.py &

# 或使用systemd服务
sudo nano /etc/systemd/system/autocopilot.service
```

systemd服务配置示例：
```ini
[Unit]
Description=AutoCopilot Agent
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/AutoCopilot
ExecStart=/usr/bin/python3 deploy/web_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📁 项目结构

```
AutoCopilot/
├── deploy/                     # 部署相关文件
│   ├── autocopilot_client.py  # 命令行客户端
│   ├── web_app.py             # Web界面版本
│   ├── build.py               # 打包脚本
│   └── requirements.txt       # 依赖列表
├── src/                        # 源代码
│   ├── agents/                # Agent定义
│   ├── tools/                # 工具函数
│   └── utils/                # 工具类
├── config/                    # 配置文件
├── assets/                    # 资源文件
└── README.md
```

---

## 🚀 使用示例

### 命令行模式

```
$ python deploy/autocopilot_client.py

╔══════════════════════════════════════════════════════════════╗
║          AutoCopilot 工业视觉检测 Agent v1.0                ║
╠══════════════════════════════════════════════════════════════╣
║  支持功能：                                                  ║
║  • 需求评估与硬件选型                                        ║
║  • 相机选型（线扫/面阵）                                     ║
║  • 光源配置推荐                                              ║
║  • 工控机配置建议                                            ║
║  • Vap SDK代码生成                                          ║
╚══════════════════════════════════════════════════════════════╝

💡 输入您的工业视觉检测需求

👤 您: 帮我分析LCD气泡检测需求，尺寸208×195mm，TT 4秒

🤖 Agent: (自动分析并输出方案)
```

### Web界面

```
1. 启动: python deploy/web_app.py
2. 打开浏览器: http://localhost:7860
3. 选择功能标签页进行操作
```

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| MIMO_API_KEY | 小米MiMo API密钥 | (必填) |
| MIMO_BASE_URL | API地址 | https://token-plan-cn.xiaomimimo.com/v1 |
| MIMO_MODEL | 模型名称 | mimo-v2.5 |
| LOCAL_MODE | 本地/远程模式 | true |

### Web界面配置

修改 `web_app.py` 中的启动参数：

```python
demo.launch(
    server_name="0.0.0.0",     # 监听地址
    server_port=7860,           # 端口
    share=False,                # 是否生成公网链接
    inbrowser=True              # 自动打开浏览器
)
```

---

## 🔍 常见问题

### Q: 打包后运行提示缺少dll?

Windows环境下需要安装 Visual C++ Redistributable：
https://aka.ms/vs/17/release/vc_redist.x64.exe

### Q: Web界面无法访问?

检查防火墙设置：
```bash
# Linux
sudo firewall-cmd --add-port=7860/tcp
sudo firewall-cmd --runtime-to-permanent
```

### Q: API请求超时?

修改超时时间或检查网络连接：
```python
response = requests.post(..., timeout=900)  # 15分钟超时
```

---

## 📞 技术支持

- GitHub: https://github.com/apintec/MegaHack-AutoCopilot
- 问题反馈: 提交Issue

---

## 📄 许可证

MIT License
