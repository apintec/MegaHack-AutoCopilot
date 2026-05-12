# MegaHack-AutoCopilot

工业自动化视觉检测智能方案设计Agent

## 功能特性

- 🔍 **需求评估**：根据产品尺寸、检测精度、TT耗时自动分析
- 📷 **硬件选型**：相机（线扫/面阵）、光源、工控机配置推荐
- 🤖 **算法推荐**：Vap SDK、InteVega SDK自动选择
- 💻 **代码生成**：自动生成检测代码（C#/Python）
- 📊 **成本估算**：设备成本、运营成本自动计算

## 快速下载exe

### Windows版本

1. **下载文件**：
   - [rebuild_exe.bat](rebuild_exe.bat) - 重组脚本
   - [AutoCopilot.exe.b64](AutoCopilot.exe.b64) - exe编码文件

2. **重组exe**：
   ```
   将两个文件放在同一目录，双击运行 rebuild_exe.bat
   ```

3. **运行**：
   ```
   双击 AutoCopilot.exe
   ```

## 本地开发运行

### Python版本（推荐）

```bash
# 克隆仓库
git clone https://github.com/apintec/MegaHack-AutoCopilot.git
cd MegaHack-AutoCopilot

# 安装依赖
pip install requests python-dotenv gradio

# 运行Web界面
python deploy/web_app.py

# 或运行命令行版本
python deploy/autocopilot_client.py
```

### 打包exe

```bash
pip install pyinstaller
pyinstaller --onefile --name AutoCopilot "deploy\autocopilot_client.py"
dist\AutoCopilot.exe
```

## 项目结构

```
MegaHack-AutoCopilot/
├── src/
│   ├── agents/          # Agent核心代码
│   ├── tools/           # 工具模块
│   └── utils/           # 工具函数
├── config/              # 配置文件
├── deploy/              # 部署脚本
│   ├── autocopilot_client.py  # 命令行客户端
│   └── web_app.py             # Web界面
├── assets/              # 资源文件
└── README.md
```

## 使用示例

### 需求分析
```
输入：液晶显示屏气泡检测，尺寸208×195mm，最小缺陷0.1mm，TT=4秒
输出：
- 相机：线扫描相机5472像素
- 光源：同轴+背光组合
- 工控机：中配(i7+RTX4060)
- 成本：约45000-90000元
```

### 代码生成
```
输入：使用Vap SDK生成16K×5000气泡检测代码
输出：完整C#检测代码（InspectionRunner.cs）
```

## 技术栈

- **Agent框架**：LangGraph/LangChain
- **视觉算法**：Vap.Algo.Badt.Fi SDK、HALCON 21.5
- **AI推理**：InteVega AI SDK
- **模型**：小米MiMo-V2.5

## 许可证

MIT License
