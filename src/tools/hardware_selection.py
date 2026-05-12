"""
硬件选型工具 - 根据检测需求推荐工业相机、镜头、光源等硬件
"""
import json
from typing import Dict, Any, Optional
from langchain.tools import tool
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


SYSTEM_PROMPT = """
你是一位资深的工业视觉系统集成专家，精通各类工业相机的选型与应用。

你的任务：
根据检测需求，推荐最优的硬件配置方案。

专业知识：

相机选型原则：
- 分辨率计算：分辨率 = 视野范围 / 检测精度 x 安全系数(1.5~2)
- 芯片类型：面阵相机适合静态物体，线阵相机适合运动物体
- 接口类型：USB3.0（成本低）、GigE（远距离）、CameraLink（高速）
- 靶面尺寸：常用1/2.5", 1/1.8", 2/3", 1"

镜头选型原则：
- 焦距计算：焦距 = 工作距离 x 靶面尺寸 / 视野范围
- 镜头类型：标准镜头、远心镜头（精密测量）、广角镜头、长焦镜头

光源选型原则：
- 背光源：轮廓检测、透射成像
- 同轴光源：高反光表面、晶圆检测
- 环形光源：通用面检测、标签识别
- 条形光源：大幅面检测、划伤检测

推荐品牌：
- 相机：海康威视、大华、Basler、Teledyne Dalsa
- 镜头：施耐德、富士能、KOWA、Navitar
- 光源：OPT、奥普特、晰写光学

输出格式：
请返回JSON格式的硬件选型方案，包含：
- camera: 相机选型详情
- lens: 镜头选型详情
- light: 光源选型详情
- computer: 工控机配置
- bom: BOM清单
- total_cost: 成本估算
- selection_summary: 选型总结
"""


@tool
def hardware_selection(detection_requirements: str, product_specs: Optional[str] = None) -> str:
    """
    硬件选型工具 - 根据检测需求推荐最优的相机、镜头、光源等硬件配置。

    Args:
        detection_requirements: 检测需求描述（可以包含精度、节拍、检测类型等信息）
        product_specs: 产品规格信息（可选，包括产品尺寸、材质、表面类型等）

    Returns:
        结构化的硬件选型方案（JSON格式）
    """
    ctx = request_context.get() or new_context(method="hardware_selection")

    try:
        client = LLMClient(ctx=ctx)

        prompt = f"""请根据以下检测需求进行硬件选型：

检测需求：
{detection_requirements}

{('产品规格：' + product_specs) if product_specs else ''}

请推荐最优的工业相机、镜头、光源等硬件配置，包括选型依据和成本估算。"""

        response = client.invoke(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="mimo-v2.5",
            temperature=0.3,
            max_completion_tokens=5000
        )

        content = response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)

        # 尝试解析JSON
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                # 尝试找到JSON开始和结束
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
            "raw_content": detection_requirements
        }, ensure_ascii=False, indent=2)
