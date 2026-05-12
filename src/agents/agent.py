"""
工业自动化视觉检测Agent - AutoCopilot
专注于为制造业客户提供智能化的视觉检测方案设计服务
"""
import os
import sys
import json
from typing import Annotated, Dict, Any, Optional, List, Tuple

# 设置PYTHONPATH确保模块导入
workspace = os.getenv('COZE_WORKSPACE_PATH', '/workspace/projects')
if workspace not in sys.path:
    sys.path.insert(0, workspace)
if os.path.join(workspace, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(workspace, 'src'))

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver

from tools import (
    requirement_analysis,
    hardware_selection,
    algorithm_recommendation,
    code_generation,
    report_generation,
    intevega_code_generation,
    intevega_model_selection,
    vap_code_generation,
    vap_module_info,
    vap_deployment_guide
)

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40


def _windowed_messages(old: list, new: list) -> list:
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    combined = add_messages(old, new)
    return list(combined)[-MAX_MESSAGES:]


def _update_project_context(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """更新项目上下文信息"""
    return {**old, **new}


class AgentState(MessagesState):
    """Agent状态定义，包含消息历史"""
    messages: Annotated[list[AnyMessage], _windowed_messages]
    project_context: Annotated[Dict[str, Any], _update_project_context]


def build_agent(ctx=None):
    """
    构建工业自动化视觉检测Agent

    Args:
        ctx: 请求上下文，用于链路追踪

    Returns:
        配置好的Agent实例
    """
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    # 读取模型配置
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # 获取API凭证（支持用户自定义配置）
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    # 初始化LLM
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        default_headers=default_headers(ctx) if ctx else {}
    )

    # 注册Agent工具
    tools = [
        requirement_analysis,
        hardware_selection,
        algorithm_recommendation,
        code_generation,
        report_generation,
        intevega_code_generation,
        intevega_model_selection
    ]

    # 创建Agent
    agent = create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )

    return agent


# Agent能力说明
CAPABILITIES = """
## 🤖 AutoCopilot - 工业自动化视觉检测专家

### 核心能力

#### 1. 需求理解与分析
- 将客户的自然语言需求转化为结构化技术指标
- 自动识别检测类型、精度要求、节拍需求
- 智能补充缺失信息，引导式需求收集

#### 2. 硬件选型推荐
- 工业相机选型（面阵/线阵、分辨率、接口）
- 镜头选型（焦距、工作距离、景深）
- 光源方案（类型、颜色、布置方式）
- BOM清单与成本估算

#### 3. 算法方案推荐
- 传统CV算法（边缘检测、Blob分析、模板匹配）
- 深度学习算法（YOLO、U-Net、异常检测）
- 预处理/后处理流程设计
- 部署方案与性能优化

#### 4. 原型代码生成
- 一键生成可运行的Python代码
- 包含主检测逻辑、配置管理、单元测试
- 支持OpenCV、PyTorch、YOLO等主流框架
- 代码可直接部署到工控机

#### 5. 方案报告输出
- 专业客户汇报文档
- 包含系统架构图、检测流程图
- 完整的BOM清单与报价
- 项目计划与风险评估

### 使用示例

**启动方案设计流程：**
```
我想做一个显示器面板的气泡检测，精度0.1mm，产能1000件/小时
```

**Agent会自动：**
1. 引导收集更多需求细节
2. 分析并结构化需求
3. 推荐硬件配置方案
4. 选择最优算法
5. 生成可运行代码
6. 输出完整方案报告
"""
