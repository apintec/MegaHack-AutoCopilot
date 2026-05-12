"""
工业视觉检测AI专家 Web界面 (Flask版本)
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
    image_data = data.get('image', '')  # 接收base64图片
    
    if not message and not image_data:
        return jsonify({'error': '请输入内容或上传图片'})
    
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
    # 系统提示词 - 工业视觉检测AI专家
    system_prompt = """你是工业视觉检测AI专家，专注于为工业自动化领域提供智能解决方案。

## 核心能力
1. **需求评估**：根据产品尺寸、检测精度、TT耗时等参数，评估检测方案可行性
2. **硬件选型**：推荐相机（线扫/面阵）、光源（同轴/背光/条光等）、工控机配置
3. **算法推荐**：推荐Vap SDK或InteVega SDK的检测算法
4. **代码生成**：生成完整的检测代码（C#/Python）
5. **方案设计**：输出符合行业标准的技术方案文档

## 技术规范（基于华星RFQ标准）
- 漏检率：<0.5%
- 误检率：<1-2%
- 像素当量计算：缺陷尺寸/2
- 线扫相机适用：TT<5秒的高速检测
- 面阵相机适用：TT>5秒的低速检测

## 光源选型指南
- 同轴光源：表面划伤、凹坑、气泡
- 背光源：透明物体内部缺陷
- 低角度环形光：边缘缺陷、刻印检测
- 条形光源：大面积均匀照明
- 穹顶光源：漫反射表面，消除反光

## 工控机配置标准（基于华星PPT）
- 高配：i9-13900K + RTX 4070Ti + 64GB（多相机系统）
- 中配：i7-12700K + RTX 4060 + 32GB（单相机系统）
- 低配：i5-12400 + RTX 3050 + 16GB（简单检测）

## 算法SDK
- Vap SDK：基于HALCON 21.5的视觉检测库，适合气泡、划伤、异物等缺陷检测
- InteVega SDK：大图推理加速，支持多线程并行处理

## 回复规范
- 使用中文回复
- 技术参数用表格展示
- 代码使用代码块
- 方案使用结构化格式
- 保持专业、简洁
"""
    
    messages.insert(0, {"role": "system", "content": system_prompt})
    
    # 如果有图片，添加到用户消息
    if image_data:
        # 构建多模态消息（图片+文字）
        user_content = [
            {"type": "text", "text": message if message else "请分析这张图片"}
        ]
        # 添加图片
        if image_data.startswith('data:image'):
            # 去掉data:image/xxx;base64,前缀
            img_data = image_data.split(',')[1] if ',' in image_data else image_data
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
            })
        messages.append({"role": "user", "content": user_content})
    else:
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
