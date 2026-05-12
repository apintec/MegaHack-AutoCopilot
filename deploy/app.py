# -*- coding: utf-8 -*-
"""
工业视觉检测AI专家 - Flask应用
支持流式输出实时显示思考过程
"""

import os
import json
import base64
import time
import re
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# API配置
API_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://token-plan-cn.xiaomimimo.com/v1')
API_KEY = os.environ.get('OPENAI_API_KEY', 'tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc')
MODEL = os.environ.get('OPENAI_MODEL', 'mimo-v2.5')

# 加载System Prompt
def load_system_prompt():
    config_path = os.path.join(os.path.dirname(__file__), 'agent_llm_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('sp', '你是一个工业视觉检测AI专家。')
    except:
        return """你是一个工业视觉检测AI专家。
你必须使用中文进行思考过程（thinking）。
在思考过程中，必须用中文逐步分析问题、展示推理逻辑、解释决策原因。
最终输出可以是中文或根据用户语言调整，但思考过程必须全部使用中文。

你擅长：
- 评估工业视觉检测需求
- 推荐相机、光源、工控机等硬件选型
- 生成Vap SDK/InteVega SDK检测代码
- 设计完整的检测技术方案"""

SYSTEM_PROMPT = load_system_prompt()

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式对话API - 实时显示思考过程"""
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    image_data = data.get('image', None)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 构建消息历史
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 添加历史对话
    for h in history[-10:]:
        if h.get('role') == 'user':
            messages.append({"role": "user", "content": h.get('content', '')})
        else:
            messages.append({"role": "assistant", "content": h.get('content', '')})
    
    # 如果有图片，添加到用户消息
    if image_data:
        user_content = [
            {"type": "text", "text": message if message else "请分析这张图片"}
        ]
        if image_data.startswith('data:image'):
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
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 4000,
        "extra_body": {
            "thinking": {
                "type": "enabled",
                "budget_tokens": 3000
            }
        }
    }
    
    def generate():
        try:
            import requests
            start_time = time.time()
            
            response = requests.post(
                f"{API_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=600
            )
            
            if response.status_code != 200:
                yield f"data: {json.dumps({'error': f'API请求失败: {response.status_code}'}, ensure_ascii=False)}\n\n"
                return
            
            # 流式读取响应
            thinking_content = ""
            answer_content = ""
            in_thinking = False
            
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get('choices')
                            if not choices:
                                continue
                            delta = choices[0].get('delta', {})
                            
                            # 检查是否有思考过程
                            if 'reasoning_content' in delta:
                                rc = delta['reasoning_content']
                                if rc:
                                    thinking_content += rc
                                    # 实时发送思考更新
                                    elapsed = round(time.time() - start_time, 1)
                                    data = {'type': 'thinking', 'content': thinking_content, 'elapsed': elapsed}
                                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                            
                            # 检查回答内容
                            if 'content' in delta:
                                content = delta['content']
                                if content:
                                    answer_content += content
                                    # 实时发送回答更新
                                    data = {'type': 'answer', 'content': answer_content}
                                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                                    
                        except json.JSONDecodeError:
                            continue
            
            # 发送完成信号
            elapsed = round(time.time() - start_time, 1)
            data = {'type': 'done', 'thinking': thinking_content, 'answer': answer_content, 'elapsed': elapsed}
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/chat', methods=['POST'])
def chat():
    """非流式对话API - 兼容旧版本"""
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    image_data = data.get('image', None)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for h in history[-10:]:
        if h.get('role') == 'user':
            messages.append({"role": "user", "content": h.get('content', '')})
        else:
            messages.append({"role": "assistant", "content": h.get('content', '')})
    
    if image_data:
        user_content = [
            {"type": "text", "text": message if message else "请分析这张图片"}
        ]
        if image_data.startswith('data:image'):
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
        "max_tokens": 4000,
        "extra_body": {
            "thinking": {
                "type": "enabled",
                "budget_tokens": 3000
            }
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=600
        )
        thinking_time = round(time.time() - start_time, 1)
        
        if response.status_code != 200:
            return jsonify({'error': f'API请求失败: {response.status_code}'})
        
        result = response.json()
        message_data = result.get('choices', [{}])[0].get('message', {})
        
        # 获取思考过程
        thinking = message_data.get('reasoning_content', '') or message_data.get('thinking', '')
        content = message_data.get('content', '')
        
        # 清理思考内容
        think_end = '</think>'
        if thinking and think_end in thinking:
            parts = thinking.split(think_end)
            if len(parts) > 1:
                thinking = parts[0].strip()
                if not content:
                    content = parts[1].strip()
        
        return jsonify({
            'response': content,
            'thinking': thinking if thinking else '',
            'thinking_time': thinking_time
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/skills/list', methods=['GET'])
def list_skills():
    """获取已安装的技能列表"""
    skills = [
        {"id": "weather", "name": "天气查询", "icon": "🌤️", "enabled": True},
        {"id": "news", "name": "新闻资讯", "icon": "📰", "enabled": False},
        {"id": "stock", "name": "股票查询", "icon": "📈", "enabled": False},
        {"id": "translate", "name": "翻译助手", "icon": "🌐", "enabled": False},
        {"id": "email", "name": "邮件发送", "icon": "📧", "enabled": False},
        {"id": "calc", "name": "计算器", "icon": "🧮", "enabled": False},
        {"id": "image_gen", "name": "图片生成", "icon": "🎨", "enabled": False},
        {"id": "doc_gen", "name": "文档处理", "icon": "📄", "enabled": False},
    ]
    return jsonify(skills)

@app.route('/api/skills/toggle', methods=['POST'])
def toggle_skill():
    """启用/禁用技能"""
    data = request.json
    skill_id = data.get('skill_id')
    enabled = data.get('enabled', False)
    return jsonify({'success': True, 'skill_id': skill_id, 'enabled': enabled})

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
