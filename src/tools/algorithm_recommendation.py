"""
算法推荐工具 - 根据检测场景推荐最优的图像处理/深度学习算法方案
"""
import json
from typing import Dict, Any, Optional
from langchain.tools import tool
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


SYSTEM_PROMPT = """
你是一位资深的计算机视觉算法专家，精通传统图像处理和深度学习算法。

你的任务：
根据检测场景，推荐最优的算法方案。

算法分类：

一、传统CV算法（基于规则）：
- 边缘检测：Canny、Sobel、Laplacian
- 形态学操作：腐蚀、膨胀、开运算、闭运算
- Blob分析：连通域标记、轮廓分析
- 模板匹配：NCC、平方差匹配
- 频域分析：傅里叶变换、Gabor滤波

二、深度学习算法：
- 目标检测：YOLOv8（高精度、高速度）、Faster R-CNN（高精度）
- 语义分割：U-Net（轻量）、DeepLabV3+（高精度）
- 异常检测：Padim（无需训练）、STPM（自监督）

算法选型原则：
- 规则明确、对比度强：传统CV算法
- 缺陷多样、场景复杂：深度学习算法
- 单类缺陷、样本少：异常检测算法
- 多类缺陷、样本充足：全监督学习

预处理算法：
- 直方图均衡化、CLAHE（对比度增强）
- 高斯滤波、中值滤波（去噪）
- 形态学预处理（开闭运算）

后处理算法：
- NMS（非极大值抑制）
- 形态学后处理
- 几何约束过滤

输出格式：
请返回JSON格式的算法方案，包含：
- algorithm_overview: 算法概述
- detection_algorithm: 检测算法详情
- preprocessing: 预处理流程
- postprocessing: 后处理流程
- alternative_algorithms: 备选算法
- deployment_recommendation: 部署建议
- development_timeline: 开发周期
"""


@tool
def algorithm_recommendation(detection_type: str, defect_types: str, accuracy_requirement: Optional[str] = None, hardware_constraint: Optional[str] = None) -> str:
    """
    算法推荐工具 - 根据检测类型和场景推荐最优的图像处理/深度学习算法方案。

    Args:
        detection_type: 检测类型（如：缺陷检测、定位、测量、分类等）
        defect_types: 缺陷类型（如：划伤、污渍、气泡、缺损等）
        accuracy_requirement: 精度要求（可选）
        hardware_constraint: 硬件约束（可选，如GPU型号、工控机配置等）

    Returns:
        结构化的算法方案（JSON格式）
    """
    ctx = request_context.get() or new_context(method="algorithm_recommendation")

    try:
        client = LLMClient(ctx=ctx)

        prompt = f"""请根据以下检测场景推荐最优的算法方案：

检测类型：{detection_type}
缺陷类型：{defect_types}
{('精度要求：' + accuracy_requirement) if accuracy_requirement else ''}
{('硬件约束：' + hardware_constraint) if hardware_constraint else ''}

请给出详细的算法选型建议，包括网络结构、预处理/后处理流程、部署方案等。"""

        response = client.invoke(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="doubao-seed-2-0-pro-260215",
            temperature=0.3,
            max_completion_tokens=6000
        )

        content = response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)

        # 尝试解析JSON
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                else:
                    json_str = content.strip()

            result = json.loads(json_str)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return content

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "raw_content": f"detection_type: {detection_type}, defect_types: {defect_types}"
        }, ensure_ascii=False, indent=2)
