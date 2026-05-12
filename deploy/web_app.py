"""
AutoCopilot Agent Web界面版本 (Gradio)
可打包为exe，支持浏览器访问
"""

import os
import sys
import json
import gradio as gr
from gradio import Theme
from dotenv import load_dotenv

load_dotenv()

# ============== 配置 ==============
class Config:
    API_KEY = os.getenv("MIMO_API_KEY", "tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc")
    API_BASE_URL = os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5")

config = Config()

# ============== Agent客户端 ==============
class AutoCopilotClient:
    """AutoCopilot工业视觉检测Agent客户端"""
    
    def __init__(self):
        import requests
        self.api_key = config.API_KEY
        self.base_url = config.API_BASE_URL
        self.model = config.MODEL
        self.history = []
    
    def chat(self, message: str, history: list) -> tuple:
        """处理用户消息"""
        import requests
        
        if not message or not message.strip():
            return "请输入内容", history
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建消息历史，添加空值检查
        messages = []
        for h in history:
            if h and len(h) >= 2:
                user_msg = h[0] if h[0] else ""
                assistant_msg = h[1] if h[1] else ""
                if user_msg:
                    messages.append({"role": "user", "content": user_msg})
                if assistant_msg:
                    messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=600
            )
            
            if response.status_code != 200:
                return f"❌ API请求失败: {response.status_code}\n\n{response.text}", history
            
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content is None:
                content = "抱歉，未获取到有效回复"
            return content, history + [[message, content]]
            
        except Exception as e:
            return f"❌ 错误: {str(e)}", history
    
    def analyze_requirement(self, product_name: str, size: str, defect_type: str, 
                           defect_size: str, tt: str, daily_output: str) -> str:
        """需求分析"""
        
        prompt = f"""请分析以下工业视觉检测需求：

产品信息：
- 产品名称：{product_name}
- 产品尺寸：{size} mm
- 缺陷类型：{defect_type}
- 最小缺陷尺寸：{defect_size} mm
- 检测节拍(TT)：{tt} 秒/件
- 日产能：{daily_output} 件

请输出完整的需求分析报告，包括：
1. 像素当量计算
2. 相机选型建议（线扫/面阵）
3. 光源选型建议
4. 工控机配置建议
5. 检测能力评估
6. 成本估算
"""
        return self.chat(prompt, [])
    
    def generate_code(self, resolution: str, pixel_size: str, task: str, module: str) -> str:
        """生成Vap SDK代码"""
        
        prompt = f"""请使用Vap SDK生成检测代码：

图像信息：
- 分辨率：{resolution}
- 像素当量：{pixel_size} um/pixel
- 检测任务：{task}
- 算法模块：{module}

请生成完整的C#代码，包括主类、配置文件和使用示例。
"""
        return self.chat(prompt, [])


# 初始化客户端
client = AutoCopilotClient()

# ============== Gradio界面 ==============
css = """
#title {
    text-align: center;
    font-size: 28px;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 20px;
}
#subtitle {
    text-align: center;
    color: #7f8c8d;
    margin-bottom: 30px;
}
.card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
}
"""

with gr.Blocks(title="AutoCopilot Agent") as demo:
    gr.Markdown("""
    # 🤖 AutoCopilot 工业视觉检测 Agent
    
    ### Industrial Vision Inspection AI Agent
    
    支持需求评估、硬件选型、算法推荐和代码生成
    """)
    
    with gr.Tabs():
        # Tab 1: 智能对话
        with gr.TabItem("💬 智能对话"):
            gr.Markdown("### 与Agent对话，输入您的工业视觉检测需求")
            chatbot = gr.Chatbot(height=500)
            msg = gr.Textbox(label="输入问题", placeholder="例如：帮我设计一个LCD面板气泡检测方案")
            with gr.Row():
                clear_btn = gr.Button("🗑️ 清空对话", variant="secondary")
                submit_btn = gr.Button("🚀 发送", variant="primary")
        
        # Tab 2: 需求分析
        with gr.TabItem("📋 需求分析"):
            gr.Markdown("### 填写产品信息，获取完整的需求分析报告")
            with gr.Row():
                with gr.Column():
                    product_name = gr.Textbox(label="产品名称", value="液晶显示屏")
                    size = gr.Textbox(label="产品尺寸 (mm)", value="208×195")
                    defect_type = gr.Textbox(label="缺陷类型", value="气泡")
                with gr.Column():
                    defect_size = gr.Textbox(label="最小缺陷尺寸 (mm)", value="0.1")
                    tt = gr.Textbox(label="TT节拍 (秒/件)", value="4")
                    daily_output = gr.Textbox(label="日产能 (件)", value="10000")
            analyze_btn = gr.Button("🔍 开始分析", variant="primary", size="lg")
            analyze_output = gr.Markdown()
        
        # Tab 3: 代码生成
        with gr.TabItem("💻 代码生成"):
            gr.Markdown("### 生成Vap SDK检测代码")
            with gr.Row():
                with gr.Column():
                    resolution = gr.Textbox(label="图像分辨率", value="16384×5000")
                    pixel_size = gr.Textbox(label="像素当量 (um)", value="13")
                with gr.Column():
                    task = gr.Textbox(label="检测任务", value="气泡检测，保护膜缺陷检测")
                    module = gr.Dropdown(
                        label="算法模块", 
                        choices=["PROTECTIVE_FILM_DEFECT", "LCD_DEFECT", "OLED_DEFECT", "GENERAL_DEFECT"],
                        value="PROTECTIVE_FILM_DEFECT"
                    )
            code_btn = gr.Button("🔧 生成代码", variant="primary", size="lg")
            code_output = gr.Code(label="生成的代码", language="cpp")
        
        # Tab 4: 关于
        with gr.TabItem("ℹ️ 关于"):
            gr.Markdown("""
            ## AutoCopilot 工业视觉检测 Agent
            
            ### 功能特性
            
            - **🤖 智能对话**: 自然语言交互，解答工业视觉检测问题
            - **📋 需求分析**: 根据产品参数自动计算硬件选型和成本估算
            - **💻 代码生成**: 一键生成Vap SDK检测代码
            - **🛠️ 方案设计**: 提供完整的检测系统设计方案
            
            ### 技术支持
            
            - 相机选型: 线扫描相机 / 面阵相机
            - 光源选型: 同轴光 / 条形光 / 背光 / 穹顶光源
            - 算法支持: Vap SDK / InteVega SDK / HALCON
            - 工控机配置: 基于华星标准的配置方案
            
            ### 联系方式
            
            - GitHub: https://github.com/apintec/MegaHack-AutoCopilot
            """)
    
    # 事件绑定
    def respond(message, history):
        response = client.chat(message, history)
        history.append((message, response))
        return "", history
    
    submit_btn.click(fn=respond, inputs=[msg, chatbot], outputs=[msg, chatbot])
    msg.submit(fn=respond, inputs=[msg, chatbot], outputs=[msg, chatbot])
    clear_btn.click(fn=lambda: ([], ""), outputs=[chatbot, msg])
    
    analyze_btn.click(
        fn=client.analyze_requirement,
        inputs=[product_name, size, defect_type, defect_size, tt, daily_output],
        outputs=analyze_output
    )
    
    code_btn.click(
        fn=client.generate_code,
        inputs=[resolution, pixel_size, task, module],
        outputs=code_output
    )


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          AutoCopilot Agent Web界面                           ║
    ║          启动中... http://localhost:7860                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        inbrowser=False
    )
