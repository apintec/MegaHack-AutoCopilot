"""
工业视觉检测AI专家 Web界面 (Flask版本)
"""

import os
import sys
import json
import time
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

# ============== 配置 ==============
API_KEY = "tp-cqp1essndwfovkwmbwlnuhse908h4r8rbzw7djmztr1ywxtc"
API_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
MODEL = "mimo-v2.5"

def estimate_tokens(text: str) -> int:
    """估算中英混合文本的 token 数量（粗略估算：中文约2字符/token，英文约0.75词/token）"""
    if not text:
        return 0
    # 中文字符约每2个字符1个token
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 非中文字符（英文、数字、标点等）约每4个字符1个token
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 2 + other_chars / 4)

# ============== 路由 ==============
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

# ============== 系统提示词 & 知识库（启动时加载一次） ==============
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_text_safe(path: str) -> str:
    """读取文本文件；失败时返回空串并打 warn 日志，不阻塞启动。"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] 读取参考资料失败: {path} ({e})", file=sys.stderr)
        return ""


# 兜底用的精简版 SP，仅在 config/agent_llm_config.json 读不到时启用
_FALLBACK_SP = """你是工业视觉检测AI专家，专注于为工业自动化领域提供智能解决方案。

## 核心能力
1. **需求评估**：根据产品尺寸、检测精度、TT耗时等参数，评估检测方案可行性
2. **硬件选型**：推荐相机（线扫/面阵）、光源（同轴/背光/条光等）、工控机配置
3. **算法推荐**：推荐Vap SDK或InteVega SDK的检测算法
4. **代码生成**：生成完整的检测代码（C#/Python）
5. **方案设计**：输出符合行业标准的技术方案文档

## 回复规范
- 使用中文回复
- 技术参数用表格展示
- 代码使用代码块
- 保持专业、简洁
"""


def _load_base_sp() -> str:
    """优先加载 config/agent_llm_config.json 里的详细 sp，读不到则用兜底版。"""
    candidate_paths = [
        os.path.join(_PROJECT_ROOT, "config", "agent_llm_config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_llm_config.json"),
    ]
    for p in candidate_paths:
        if not os.path.isfile(p):
            continue
        try:
            with open(p, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            sp = (cfg.get('sp') or '').strip()
            if sp:
                print(f"[INFO] 已加载详细 system prompt: {p} ({len(sp)} 字符)")
                return sp
        except Exception as e:
            print(f"[WARN] 解析 {p} 失败: {e}", file=sys.stderr)
    print("[WARN] 未找到 agent_llm_config.json，使用兜底精简 SP", file=sys.stderr)
    return _FALLBACK_SP


_BASE_SP = _load_base_sp()

# SDK 详细文档（真实 API、结构体、调用流程）——按需注入，避免常规对话浪费 token
_INTEVEGA_DOC = _read_text_safe(
    os.path.join(_PROJECT_ROOT, "assets", "SDK_speed_up_Instruction_document.md")
)
_VAP_DOC = _read_text_safe(
    os.path.join(_PROJECT_ROOT, "assets", "Vap.Algo.Badt.Fi_API手册.md")
)
print(f"[INFO] 知识库加载: InteVega={len(_INTEVEGA_DOC)} chars, Vap={len(_VAP_DOC)} chars")

# 前端可视化能力说明：告诉模型本前端能直接渲染哪些图表
_RENDER_CAPABILITIES = """

# 可视化输出能力（重要）
本前端已集成 Mermaid 渲染引擎，可以**直接展示**流程图等可视化图表，无需用户复制到外部工具。
- 当用户要求"流程图 / 时序图 / 状态图 / 思维导图 / 类图 / 甘特图 / 架构图"时，**必须使用 ```mermaid 代码块**输出 Mermaid 语法。系统会自动渲染为可视化图表（并提供 SVG/PNG 下载、复制源码按钮）。
- **严禁**再说"请在 VS Code / Typora / GitHub 中渲染"或"复制到 Mermaid 编辑器查看"——本系统直接显示。
- 节点标签使用中文，保持简洁（建议 ≤ 20 个节点，过长图请拆分为多个）。
- 推荐图类型：
  - 算法/业务流程 → `flowchart TD` 或 `flowchart LR`
  - 调用时序 → `sequenceDiagram`
  - 状态机 → `stateDiagram-v2`
  - 类结构 → `classDiagram`
  - 时间排程 → `gantt`
- 代码块外可补一句简短文字说明，但不要重复贴一遍 Mermaid 源码。

代码生成（C# / Python 等）走 ```cs / ```python 代码块，前端会自动转成"文件卡片"，点击可打开右侧抽屉预览，可复制、可下载为对应文件（.cs / .py 等）。
"""

# 注入参考资料时附加的"使用规则"——告诉模型必须基于文档而非凭空生成
_KB_USAGE_RULES = """
# 参考资料使用规则（强制）
下文「参考资料」节给出了相关 SDK 的真实 C# API、结构体定义和调用流程，请严格遵守：
1. **不允许虚构 API**：生成代码时函数名、结构体字段、枚举值必须来自参考资料；
   若文档未涵盖，明确告知"该 API 在已知文档中未提供"，不要凭空猜测。
2. **必须命中真实 API**：每个 SDK 的核心调用代码必须出现 ≥ 5 个文档里出现过
   的函数名 / 结构体名（如 `mallocImgBufferOnCUDA`、`TBboxScoreInfo` 等）。
   如果通篇都是 `using OpenCvSharp;` 的图像处理逻辑而没有 SDK 函数，视为跑题。
3. **优先复用文档代码片段**：GPU 内存申请、图像拷贝、推理句柄创建、结果解析等
   通用步骤，直接引用文档示例。
4. **完整调用流程**：包含初始化、推理、结果解析、资源释放（避免内存泄漏）。
5. **理解 SDK 定位**：阅读注入文档后，先在心里区分这是"算法实现库"还是
   "部署/推理引擎"——
   - 部署/推理引擎（如 InteVega）：用户的"用 XX 写气泡检测"应理解为
     "训练气泡模型 + 用 SDK 部署"，不要把它当算法库。
   - 算法实现库（如 Vap.Algo.Badt.Fi）：直接调用 SDK 内置的 InspectionAlgo。
6. **代码末尾**：用一句话指出参考了文档哪一节（例："参考: §3 目标检测使用示例"）。
"""

# Vap SDK 的"语言锁"——只要识别到 Vap 场景，回答必须是 C#
_VAP_LANG_LOCK = """
# ⚠️ 语言强制规则（针对本次问题）
本问题涉及 **Vap.Algo.Badt.Fi**，是一个 **C# / .NET Standard 2.1 程序集**
（程序集名 `Vap.Algo.Badt.Fi.dll`，依赖 `HalconDotNet` v21.5），**不存在 Python 绑定**。回答必须遵守：
1. 所有代码块使用 ```csharp 标记；**严禁** ```python / import / def / numpy / OpenCV / PIL。
2. 类名、命名空间、方法签名一律从下文参考资料拷贝（如
   `Vap.Algo.Badt.Fi.Base.IAlgoBase<TInput,TParam,TResult>`、
   `BaseInspectionAlgo<,,>`、`Vap.Algo.Badt.Fi.Detect.Bubble.*` 等）。
3. 图像输入用 `HObject` 或 `byte[]`（参考手册 §8），**不要**用 OpenCV / PIL / numpy.array。
4. 工程目标框架 `netstandard2.1` 或 `.NET 6+`，请给出可直接放入 .cs 文件的内容。
5. 如用户明确要求 Python：直接告知"Vap SDK 仅提供 C# (.NET) 接口，没有 Python 绑定"，
   可建议通过 HTTP/gRPC 包装 C# 服务后让 Python 客户端调用，**不要凭空编造 Python API**。
"""

# InteVega SDK 也是 C# 原生
# 关键认知：InteVega 是"大图加速推理引擎"（部署 SDK），不是"算法设计库"。
# 用户说"基于 InteVega 设计气泡检测算法"时，真正的含义是：
#   先训练一个气泡检测模型 → 转成 InteVega 支持的格式 → 用 SDK 部署推理。
# 如果不锚定这一点，LLM 会跑题写一段通用 C# 图像处理逻辑，完全用不到 SDK。
_INTEVEGA_LANG_LOCK = """
# ⚠️ 语言 & API 强制规则（针对本次问题）

## 1. 本质认知（务必先理解）
**InteVega SDK 是 C# 大图加速推理引擎（部署运行时）**，**不是算法设计库**。
它负责把训练好的目标检测 / 语义分割 / 稠密点定位 / 分类模型，以"大图切片 +
GPU 加速 + 结果合并"的方式跑在 NVIDIA GPU 上。它本身不包含"气泡检测算法"，
而是负责跑你训练好的"气泡检测模型"。

## 2. 用户问"基于 InteVega 写 XX 检测"时的正确解读
方案要包含两部分，**缺一不可**：
- **(A) 模型层**：建议训练 YOLO / U-Net / 分类等模型用于 XX 检测，
  给出数据准备、训练框架、推荐网络结构、模型导出格式（推荐 ONNX / RKNN /
  TensorRT，最终需打包成 SDK 支持的 hslp.json + 权重）。
- **(B) 部署层（代码主体）**：用 InteVega SDK 完整调用模型推理，**代码必须
  严格走文档 §3 "目标检测使用示例" 的 5 步流程**：
  1) `mallocImgBufferOnCUDA` 预申请 GPU 显存
  2) `parseJsonToOpenParam` 解析模型配置 + `createDetectorHandle` 创建推理句柄
  3) `ConvertMatToTImageInfo` 把 OpenCV `Mat` 转 `TImageInfo` 并拷到 GPU
  4) `inferDetectorAnalysisPtr` 调用推理，解析 `TBboxScoreInfo`
  5) `releaseDetectorInfoPtr` 释放结果，结束时释放 GPU 显存

## 3. 必须命中的真实 API（反幻觉硬约束）
代码至少要出现以下 SDK 函数/结构体的 **5 个以上**，名称必须与下文一字不差：
- 函数：`mallocImgBufferOnCUDA`、`createDetectorHandle`、`parseJsonToOpenParam`、
  `inferDetectorAnalysisPtr`、`releaseDetectorInfoPtr`、`copyImgBufferFromCpuToGpu`、
  `setupDetectorLogLevel`、`getDetectorVersion`、`getAIErrorMessage`、
  `ConvertMatToTImageInfo`
- 结构体：`TModelOpenParam`、`TImageInfo`、`TBboxScoreInfo`、
  `TSingleDetectorInfoPtr`、`TBatchDetectorOutInfoPtr`、`TBbox`、
  `EImageFmt`（如 `AI_BGR_U8C3`、`AI_GRAY_U8C1`）、`EDataAddrType`（如 `AI_DATA_ADDR_GPU`）
**严禁**自创 `IntelVega.Detector.Run()` / `InteVegaSDK.Detect()` 这种文档里
没有的虚构 API。

## 4. 语言锁
1. 所有代码块使用 ```csharp 标记；**严禁** ```python / ```cpp 作为主代码。
2. 如用户要求 Python：先说明 InteVega 原生接口为 C# (P/Invoke + native dll)，
   再给出"在 C# 工程里包一层 HTTP/gRPC 服务、Python 客户端调用"的思路，
   **不要**凭空写 Python 调用代码。

## 5. 必备结尾
代码末尾用一句中文标明参考的文档章节，如：
"参考: §3 目标检测使用示例 / §2 GPU 显存的申请与释放"。
"""

# 关键字触发表：用户消息或历史里命中即注入对应文档
# 思路：除了 SDK 自身专有名词，还要兜住用户用"业务语言"描述场景的情况
# （例如"气泡检测/缺陷检测/HALCON"——这些场景在本工程里只有 Vap 能做，必须命中）
_INTEVEGA_KEYWORDS = (
    # SDK 名称变体
    'intevega', 'inte vega', 'inte-vega', 'intelvega',
    # API 专有名
    'ovg', 'tvg', 'slicewidth', 'sliceheight', 'sliceoverlooprate',
    'inferdetectoranalysis', 'createdetectorhandle', 'mallocimgbufferoncuda',
    'tmodelopenparam', 'tbboxscoreinfo',
    # 中文业务场景（仅在没有 Vap 命中时由 InteVega 兜底；本工程里大图推理 = InteVega）
    '大图推理', '大图加速', '推理加速', '切片推理', '大图检测',
)
_VAP_KEYWORDS = (
    # SDK 名称与程序集
    'vap', 'badt.fi', 'badt', 'vap.algo', 'algo.badt',
    # 依赖 / 输入类型
    'halcon', 'halcondotnet', 'hobject', 'hdevelop',
    # 核心类型
    'ialgobase', 'baseinspectionalgo', 'basealgoinput', 'basealgoparam',
    'basealgoresult', 'singledefect', 'algomodule', 'defecttype',
    'inspectionalgo', 'algomoduleattribute', 'propertyeditorattribute',
    # 具体检测算法
    'bubbledetect', 'bubble',
    # 中文业务场景：在本工程里这些只能用 Vap 实现
    '气泡', '气泡检测', '缺陷检测', '表面检测',
    '划伤', '划痕', '凹坑', '异物',
    '视觉检测sdk', 'badt 现场',
)


# 用户"显式点名"某个 SDK 的强信号——只要消息里明确出现这些专名，
# 就认为用户指定了这一家，另一家 SDK 的文档不再注入（避免 LLM 拿现成示例跑题）
_INTEVEGA_NAME_HITS = ('intevega', 'inte vega', 'inte-vega', 'intelvega')
_VAP_NAME_HITS = ('vap', 'badt.fi', 'badt', 'vap.algo', 'algo.badt')


def _build_kb_block(message: str, history) -> str:
    """根据用户上下文挑选要注入的 SDK 文档 + 语言锁，按关键字门控以节省 token。

    决策规则：
    1. 仅扫"本次用户消息"（不带 history）做"显式点名"判定——历史里的另一家 SDK
       不应污染当前轮的语言锁
    2. 如果当前消息显式点名了 InteVega 或 Vap，且只点了其中一个 → 锁定该 SDK，
       屏蔽另一家的文档与语言锁
    3. 否则按"用户消息 + 历史"的全局关键字命中表，两家都注入
    """
    # 当前轮显式点名
    current = (message or '').lower()
    cur_intevega_name = any(k in current for k in _INTEVEGA_NAME_HITS)
    cur_vap_name = any(k in current for k in _VAP_NAME_HITS)
    exclusive = None
    if cur_intevega_name and not cur_vap_name:
        exclusive = 'intevega'
    elif cur_vap_name and not cur_intevega_name:
        exclusive = 'vap'

    # 全局命中（消息 + 历史）：兜住业务关键词
    parts = [(message or '')]
    for h in (history or []):
        if h and len(h) >= 2:
            parts.append(h[0] or '')
            parts.append(h[1] or '')
    haystack = ' '.join(parts).lower()

    intevega_hits = [k for k in _INTEVEGA_KEYWORDS if k in haystack]
    vap_hits = [k for k in _VAP_KEYWORDS if k in haystack]

    inject_intevega = bool(_INTEVEGA_DOC and intevega_hits) and exclusive != 'vap'
    inject_vap = bool(_VAP_DOC and vap_hits) and exclusive != 'intevega'

    blocks: list[str] = []
    locks: list[str] = []

    if inject_intevega:
        locks.append(_INTEVEGA_LANG_LOCK)
        blocks.append(
            "## 【参考资料 A】InteVega SDK 大图加速推理使用说明（C# / .NET）\n\n" + _INTEVEGA_DOC
        )
    if inject_vap:
        locks.append(_VAP_LANG_LOCK)
        blocks.append(
            "## 【参考资料 B】Vap.Algo.Badt.Fi API 手册（C# / .NET）\n\n" + _VAP_DOC
        )

    # 调试可见性：命中了什么、是否触发了"独占锁定"、最终注入多少字符
    if intevega_hits or vap_hits:
        print(
            f"[KB] exclusive={exclusive or '-'} | "
            f"hits intevega={intevega_hits or '-'}, vap={vap_hits or '-'} | "
            f"inject intevega={inject_intevega}, vap={inject_vap}, "
            f"chars={sum(len(b) for b in blocks)}",
            flush=True,
        )

    if not blocks:
        return ""
    return (
        _KB_USAGE_RULES
        + "\n".join(locks)
        + "\n\n# 参考资料\n\n"
        + "\n\n---\n\n".join(blocks)
    )


# 语言/SDK 默认偏好——固定写在每次 SP 末尾，弥补 _BASE_SP 里"C#/Python"二选一的歧义
_LANG_PREFERENCE = """

# SDK 与语言默认偏好（必须遵守）
本工程支持的两个核心 SDK **全部为 C# / .NET**：
- **Vap.Algo.Badt.Fi**：C# (.NET Standard 2.1) + HalconDotNet 21.5，**没有 Python 绑定**
- **InteVega SDK**：大图加速推理库，官方接口为 C#

回答规则：
1. 如果用户问题命中以上任一 SDK（直接点名、或描述属于其负责的检测场景，
   例如气泡/划伤/缺陷/表面检测/大图推理加速），代码默认输出 ```csharp，**严禁**默认输出 Python。
2. 仅当用户**明确**说"用 Python / 给我 Python 代码 / Python 调用"时，再考虑 Python；
   此时也要先声明 "Vap/InteVega 没有原生 Python 绑定"，再给出 HTTP/gRPC 或 P/Invoke 包装方案。
3. 如果用户问题与上面两个 SDK 都不相关（例如纯算法原理讨论、Mermaid 流程图、文档撰写），
   则按用户偏好选语言，没有限制。
"""


def _build_system_prompt(message: str, history) -> str:
    """合成最终 system prompt：基础 SP + 前端能力声明 + 语言偏好 + 按需注入的 SDK 文档块。"""
    return _BASE_SP + _RENDER_CAPABILITIES + _LANG_PREFERENCE + _build_kb_block(message, history)

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式对话API - 实时显示思考过程"""
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    image_data = data.get('image', '')
    
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
    
    # 动态拼接 system prompt：基础 SP + 按需注入的 SDK 详细文档
    # 这样问"用 InteVega SDK 写..."时，模型能看到真实 API 与结构体定义，
    # 而不是只看到一句"InteVega SDK：大图推理加速"导致凭空生成
    full_sp = _build_system_prompt(message, history)
    messages.insert(0, {"role": "system", "content": full_sp})
    
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
        # 8000：足够装下数百行 SDK 代码 + 中文说明 + 二级示例（如 Program.cs）。
        # 之前 4000 在生成完 BubbleDefect.cs 这种长文件后，Program.cs 会被截断。
        "max_tokens": 8000,
        "extra_body": {
            "thinking": {
                "type": "enabled",
                "budget_tokens": 3000
            }
        }
    }
    
    def generate():
        # 击穿浏览器 SSE 首字节缓冲（Chrome/Edge 大约 2KB），先送一条注释占位
        # 这样首个真实事件就能立刻被前端 EventSource 触发
        yield ':' + (' ' * 2048) + '\n\n'

        start_time = time.time()
        thinking_content = ""
        answer_content = ""
        buffer = b""

        def _emit(payload_dict):
            return 'data: ' + json.dumps(payload_dict, ensure_ascii=False) + '\n\n'

        def _parse_delta(raw_line: bytes):
            """解析一条 SSE data 行，返回 (rc_text, content_text, is_done)"""
            line = raw_line.strip()
            if not line or not line.startswith(b'data: '):
                return None, None, False
            data_str = line[6:].decode('utf-8', errors='replace')
            if data_str == '[DONE]':
                return None, None, True
            try:
                chunk_obj = json.loads(data_str)
            except json.JSONDecodeError:
                return None, None, False
            choices = chunk_obj.get('choices', [])
            if not choices:
                return None, None, False
            delta = choices[0].get('delta', {}) or {}
            return delta.get('reasoning_content'), delta.get('content'), False

        # timeout=(connect, read)：
        # - connect 15s：上游不可达时快速失败
        # - read 300s：覆盖两种场景——
        #     a) 上传 body 的 socket write 等待（图片 base64 可达数 MB）
        #     b) 两次成功 read 之间的最大间隔
        upstream_timeout = (15, 300)
        response = None
        try:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=upstream_timeout,
                )
            except requests.exceptions.ConnectTimeout:
                yield _emit({'type': 'error', 'error': f'上游连接超时（>{upstream_timeout[0]}s 未建立 TCP），请检查网络后重试'})
                return
            except requests.exceptions.ReadTimeout:
                yield _emit({'type': 'error', 'error': f'上游首字节响应超时（>{upstream_timeout[1]}s）'})
                return
            except requests.exceptions.ConnectionError as e:
                err_str = str(e).lower()
                if 'write operation' in err_str or 'broken pipe' in err_str:
                    msg = '请求体发送超时（图片体积较大或网络较慢），可尝试压缩图片后重试'
                elif 'aborted' in err_str:
                    msg = '上游连接被中断，请稍后重试'
                else:
                    msg = f'上游连接失败: {e}'
                yield _emit({'type': 'error', 'error': msg})
                return

            if response.status_code != 200:
                # 把上游 body 前 500 字节带回来，便于定位（如 context 超长、限流、鉴权等）
                body_preview = ''
                try:
                    raw = b''
                    for piece in response.iter_content(chunk_size=512):
                        raw += piece
                        if len(raw) >= 512:
                            break
                    body_preview = raw.decode('utf-8', errors='replace')[:500]
                except Exception:
                    pass
                yield _emit({
                    'type': 'error',
                    'error': f'API请求失败: HTTP {response.status_code} | {body_preview}',
                })
                return

            # chunk_size=None：urllib3 一拿到 HTTP chunk 就吐给我们，
            # 自己按 \n 拆 SSE，避免 iter_lines 的行级累积
            done_flag = False
            try:
                for chunk in response.iter_content(chunk_size=None, decode_unicode=False):
                    if not chunk:
                        continue
                    buffer += chunk
                    while b'\n' in buffer:
                        raw_line, _, buffer = buffer.partition(b'\n')
                        rc, content, is_done = _parse_delta(raw_line)
                        if is_done:
                            done_flag = True
                            buffer = b''
                            break
                        if rc:
                            thinking_content += rc
                            yield _emit({
                                'type': 'thinking',
                                'content': thinking_content,
                                'elapsed': round(time.time() - start_time, 1),
                            })
                        if content:
                            answer_content += content
                            yield _emit({
                                'type': 'answer',
                                'content': answer_content,
                                'elapsed': round(time.time() - start_time, 1),
                            })
                    if done_flag:
                        break
            except requests.exceptions.ReadTimeout:
                # 上游 token 之间长时间无字节：告知前端并优雅收尾
                yield _emit({
                    'type': 'error',
                    'error': f'上游响应中断（>{upstream_timeout[1]}s 无数据）',
                })
                return
            except requests.exceptions.ChunkedEncodingError as e:
                # 上游链路中途断流
                yield _emit({'type': 'error', 'error': f'上游响应被中断: {e}'})
                return

            # 估算 token 使用量（粗略估算）
            # 输入 = system prompt + 历史消息 + 当前消息
            # 注意：这里只计算当前消息和历史记录，实际 token 以 API 返回为准
            input_text = str(history) + ' ' + message
            prompt_tokens = estimate_tokens(input_text)
            thinking_tokens = estimate_tokens(thinking_content)
            completion_tokens = estimate_tokens(answer_content)
            total_tokens = prompt_tokens + thinking_tokens + completion_tokens

            yield _emit({
                'type': 'done',
                'thinking': thinking_content,
                'answer': answer_content,
                'elapsed': round(time.time() - start_time, 1),
                'usage': {
                    'prompt_tokens': prompt_tokens,
                    'thinking_tokens': thinking_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                }
            })

        except GeneratorExit:
            # 客户端断开连接（fetch abort / 浏览器关闭）：不要把它当 error 发，
            # 让 finally 关闭上游连接即可
            raise
        except Exception as e:
            yield _emit({'type': 'error', 'error': str(e)})
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    sse_headers = {
        'Cache-Control': 'no-cache, no-transform',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=sse_headers,
    )

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
- Vap = Vision AI Project（视觉AI项目的统称）
- Badt.Fi = Badt现场的Fi项目专用算法
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
        
        # 获取思考过程（如果模型支持）
        thinking = message_data.get('reasoning_content', '') or message_data.get('thinking', '')
        content = message_data.get('content', '')
        
        if content is None or content == '':
            content = "抱歉，未获取到有效回复"
        
        # 如果没有thinking字段，尝试从content中提取
        if not thinking and '<think>' in content:
            # 尝试分离思考和回答
            parts = content.split('</think>')
            if len(parts) > 1:
                thinking = parts[0].replace('<think>', '').strip()
                content = parts[1].strip()
        
        return jsonify({
            'response': content,
            'thinking': thinking if thinking else '',
            'thinking_time': thinking_time
        })
        
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

# ============== Skill管理API ==============

@app.route('/api/skills/list', methods=['GET'])
def list_skills():
    """获取可用和已安装的Skill列表"""
    try:
        from src.utils.skill_manager import skill_manager
        available = skill_manager.list_available_skills()
        return jsonify({'skills': available})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/skills/install', methods=['POST'])
def install_skill():
    """安装指定Skill"""
    data = request.json
    skill_name = data.get('skill_name', '')
    
    if not skill_name:
        return jsonify({'error': '请指定要安装的Skill名称'})
    
    try:
        from src.utils.skill_manager import skill_manager
        result = skill_manager.install_skill(skill_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/skills/uninstall', methods=['POST'])
def uninstall_skill():
    """卸载指定Skill"""
    data = request.json
    skill_name = data.get('skill_name', '')
    
    if not skill_name:
        return jsonify({'error': '请指定要卸载的Skill名称'})
    
    try:
        from src.utils.skill_manager import skill_manager
        result = skill_manager.uninstall_skill(skill_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/skills/execute', methods=['POST'])
def execute_skill():
    """执行Skill功能"""
    data = request.json
    skill_type = data.get('skill_type', '')
    params = data.get('params', {})
    
    try:
        from src.tools.skill_tools import execute_weather_query, execute_translation
        
        if skill_type == 'weather':
            city = params.get('city', '')
            result = execute_weather_query.invoke({'city': city})
            return jsonify({'result': result})
        elif skill_type == 'translation':
            text = params.get('text', '')
            target = params.get('target_lang', 'en')
            result = execute_translation.invoke({'text': text, 'target_lang': target})
            return jsonify({'result': result})
        else:
            return jsonify({'error': f'未知的Skill类型: {skill_type}'})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║          AutoCopilot Agent Web界面                           ║
    ║          启动中... http://localhost:8080                    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    # threaded=True 确保 SSE 长连接独占一个线程，不阻塞其它请求；
    # use_reloader=False 避免 reloader 进程包裹导致的 stdio/socket 缓冲
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True, use_reloader=False)
