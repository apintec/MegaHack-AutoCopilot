"""
AutoCopilot Agent 独立客户端
支持本地运行和远程服务连接两种模式
"""

import os
import sys
import json
import argparse
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# ============== 配置 ==============
class Config:
    # 远程Agent服务地址（部署后填入）
    REMOTE_AGENT_URL = os.getenv("REMOTE_AGENT_URL", "https://your-agent-service.coze.cn/api/chat")
    
    # 本地模式：使用自己的API Key
    LOCAL_MODE = os.getenv("LOCAL_MODE", "true").lower() == "true"
    
    # 小米MiMo API配置
    API_KEY = os.getenv("MIMO_API_KEY", "tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc")
    API_BASE_URL = os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5")

config = Config()

# ============== Agent客户端 ==============
class AutoCopilotClient:
    """AutoCopilot工业视觉检测Agent客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or config.API_KEY
        self.base_url = base_url or config.API_BASE_URL
        self.model = model or config.MODEL
        self.session_id = None
    
    def chat(self, message: str, stream: bool = True) -> Dict[str, Any]:
        """
        发送消息给Agent
        
        Args:
            message: 用户输入的消息
            stream: 是否流式输出
        
        Returns:
            Agent响应结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=600,
                stream=stream
            )
            
            if response.status_code != 200:
                return {"error": f"API请求失败: {response.status_code}", "detail": response.text}
            
            if stream:
                # 流式响应处理
                full_content = []
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            data = line_text[6:]
                            if data == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        print(content, end='', flush=True)
                                        full_content.append(content)
                            except json.JSONDecodeError:
                                continue
                print()  # 换行
                return {"content": ''.join(full_content), "status": "success"}
            else:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                return {"content": content, "status": "success"}
                
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def analyze_requirement(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        需求分析接口
        
        Args:
            product_info: 产品信息字典
                - product_name: 产品名称
                - product_size_mm: 产品尺寸 (如 "208×195")
                - defect_type: 缺陷类型
                - defect_size_mm: 最小缺陷尺寸
                - tt_seconds: TT节拍(秒)
                - daily_output: 日产能
        
        Returns:
            分析结果
        """
        prompt = f"""请分析以下工业视觉检测需求：

产品信息：
- 产品名称：{product_info.get('product_name', '未知')}
- 产品尺寸：{product_info.get('product_size_mm', '未知')} mm
- 缺陷类型：{product_info.get('defect_type', '未知')}
- 最小缺陷尺寸：{product_info.get('defect_size_mm', '未知')} mm
- 检测节拍(TT)：{product_info.get('tt_seconds', '未知')} 秒/件
- 日产能：{product_info.get('daily_output', '未知')} 件

请输出：
1. 像素当量计算
2. 相机选型建议（线扫/面阵）
3. 光源选型建议
4. 工控机配置建议
5. 检测能力评估
6. 成本估算
"""
        return self.chat(prompt, stream=True)
    
    def generate_vap_code(self, image_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成Vap SDK检测代码
        
        Args:
            image_info: 图像信息
                - image_resolution: 图像分辨率 (如 "16384×5000")
                - resolution_um: 像素当量 (um)
                - detection_task: 检测任务描述
                - algorithm_module: 算法模块
        """
        prompt = f"""请使用Vap SDK生成检测代码：

图像信息：
- 分辨率：{image_info.get('image_resolution', '16384×5000')}
- 像素当量：{image_info.get('resolution_um', 13)} um/pixel
- 检测任务：{image_info.get('detection_task', '气泡检测')}
- 算法模块：{image_info.get('algorithm_module', 'PROTECTIVE_FILM_DEFECT')}

请生成完整的C#代码，包括：
1. InspectionRunner.cs 主类
2. 项目配置文件
3. 模型配置文件
4. 使用示例
"""
        return self.chat(prompt, stream=True)


# ============== 命令行界面 ==============
def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          AutoCopilot 工业视觉检测 Agent v1.0                ║
║          Industrial Vision Inspection AI Agent              ║
╠══════════════════════════════════════════════════════════════╣
║  支持功能：                                                  ║
║  • 需求评估与硬件选型                                        ║
║  • 相机选型（线扫/面阵）                                     ║
║  • 光源配置推荐                                              ║
║  • 工控机配置建议                                            ║
║  • Vap SDK代码生成                                          ║
║  • 检测方案设计                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

def interactive_mode(client: AutoCopilotClient):
    """交互式对话模式"""
    print_banner()
    print("💡 输入您的工业视觉检测需求，按回车发送，输入 'quit' 退出\n")
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Agent: ", end='', flush=True)
            result = client.chat(user_input, stream=True)
            
            if result.get("status") == "error":
                print(f"\n❌ 错误: {result.get('error')}")
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 异常: {e}")

def quick_analyze(client: AutoCopilotClient):
    """快速需求分析"""
    print("\n📋 快速需求分析")
    print("-" * 50)
    
    product_info = {
        'product_name': input("产品名称: ") or "工业产品",
        'product_size_mm': input("产品尺寸 (如 208×195): ") or "100×100",
        'defect_type': input("缺陷类型 (如 气泡/划伤/污渍): ") or "气泡",
        'defect_size_mm': input("最小缺陷尺寸 (mm): ") or "0.1",
        'tt_seconds': input("TT节拍 (秒/件): ") or "5",
        'daily_output': input("日产能 (件): ") or "10000"
    }
    
    print("\n🔄 分析中...\n")
    result = client.analyze_requirement(product_info)
    
    return result

def main():
    parser = argparse.ArgumentParser(description="AutoCopilot 工业视觉检测 Agent")
    parser.add_argument("--mode", "-m", choices=["chat", "analyze", "codegen"], 
                       default="chat", help="运行模式")
    parser.add_argument("--api-key", help="API Key (默认使用环境变量)")
    parser.add_argument("--base-url", help="API Base URL")
    parser.add_argument("--model", "-M", help="模型名称")
    parser.add_argument("--product", "-p", help="产品信息JSON文件")
    
    args = parser.parse_args()
    
    # 初始化客户端
    client = AutoCopilotClient(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model
    )
    
    # 根据模式运行
    if args.mode == "chat":
        interactive_mode(client)
    elif args.mode == "analyze":
        quick_analyze(client)
    elif args.mode == "codegen":
        print("\n🔧 Vap SDK代码生成")
        print("-" * 50)
        image_info = {
            'image_resolution': input("图像分辨率 (默认 16384×5000): ") or "16384×5000",
            'resolution_um': input("像素当量 um (默认 13): ") or "13",
            'detection_task': input("检测任务: ") or "气泡检测",
            'algorithm_module': input("算法模块: ") or "PROTECTIVE_FILM_DEFECT"
        }
        print("\n🔄 生成代码中...\n")
        client.generate_vap_code(image_info)


if __name__ == "__main__":
    main()
