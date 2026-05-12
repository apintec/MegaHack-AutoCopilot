"""
需求分析工具 - 将用户模糊需求转化为结构化技术指标
"""
import json
from typing import Dict, Any, Optional
from langchain.tools import tool
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


SYSTEM_PROMPT = """
你是一位资深的工业视觉工程师，擅长将客户的模糊需求转化为精确的技术指标。

你的任务：
分析用户描述的检测需求，提取并结构化以下关键信息：

必填字段：
1. product_name: 产品名称
2. product_type: 产品类型（电子元件、食品药品、医疗器械、汽车零部件等）
3. detection_type: 检测类型（定位/测量/缺陷检测/识别分类/装配检测）
4. defect_types: 缺陷类型列表
5. accuracy_requirement: 精度要求
6. throughput: 生产节拍
7. product_specs: 产品规格
8. environment: 工作环境

输出格式：
请返回JSON格式的结构化数据，包含：
- product_name, product_type, detection_type
- defect_types: 缺陷类型列表
- accuracy_requirement: 精度要求详情
- throughput: 产能和节拍要求
- product_specs: 产品尺寸、材质、表面类型
- environment: 工作环境详情
- missing_info: 缺失信息列表
- confidence: 分析可信度
- analysis_summary: 分析总结
"""


@tool
def requirement_analysis(user_requirement: str, available_info: Optional[str] = None) -> str:
    """
    需求分析工具 - 将用户的自然语言需求转化为结构化技术指标。

    Args:
        user_requirement: 用户描述的检测需求（如：我要检测显示器面板上的气泡，要求精度0.1mm，产能1000件/小时）
        available_info: 已收集到的其他信息（可选）

    Returns:
        结构化的需求分析结果（JSON格式）
    """
    ctx = request_context.get() or new_context(method="requirement_analysis")

    try:
        client = LLMClient(ctx=ctx)

        prompt = f"""请分析以下工业视觉检测需求：

用户需求：{user_requirement}

{('已收集信息：' + available_info) if available_info else ''}

请提取并结构化所有关键技术指标。"""

        response = client.invoke(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="mimo-v2.5",
            temperature=0.3,
            max_completion_tokens=4000
        )

        content = response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)

        # 尝试解析JSON
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            # 如果不是有效JSON，返回原始内容
            return content

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "raw_content": user_requirement
        }, ensure_ascii=False, indent=2)
