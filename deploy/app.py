"""
AutoCopilot Agent Web界面 (Flask版本)
"""

import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============== 配置 ==============
API_KEY = "tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc"
API_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MODEL = "mimo-v2.5"

# ============== 路由 ==============
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """处理对话请求"""
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    
    if not message:
        return jsonify({'error': '请输入内容'})
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 构建消息历史
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
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=600
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'API请求失败: {response.status_code}'})
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if content is None:
            content = "抱歉，未获取到有效回复"
        
        return jsonify({'response': content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """需求分析"""
    data = request.json
    
    product_name = data.get('product_name', '')
    size = data.get('size', '')
    defect_type = data.get('defect_type', '')
    defect_size = data.get('defect_size', '')
    tt = data.get('tt', '')
    daily_output = data.get('daily_output', '')
    
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
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=600
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'API请求失败: {response.status_code}'})
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if content is None:
            content = "抱歉，未获取到有效回复"
        
        return jsonify({'response': content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/generate', methods=['POST'])
def generate():
    """生成Vap SDK代码"""
    data = request.json
    
    resolution = data.get('resolution', '')
    pixel_size = data.get('pixel_size', '')
    task = data.get('task', '')
    module = data.get('module', '')
    
    prompt = f"""请使用Vap SDK生成检测代码：

图像信息：
- 分辨率：{resolution}
- 像素当量：{pixel_size} um/pixel
- 检测任务：{task}
- 算法模块：{module}

请生成完整的C#代码，包括主类、配置文件和使用示例。
"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=600
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'API请求失败: {response.status_code}'})
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if content is None:
            content = "抱歉，未获取到有效回复"
        
        return jsonify({'response': content})
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          AutoCopilot Agent Web界面                           ║
    ║          启动中... http://localhost:8080                    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=8080, debug=False)
