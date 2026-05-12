"""
方案报告生成工具 - 根据检测方案生成完整的项目方案报告
"""
import json
from typing import Dict, Any, Optional
from langchain.tools import tool
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


SYSTEM_PROMPT = """
你是一位资深的技术方案专家，擅长编写专业的工业自动化项目方案报告。

报告结构：

1. 项目概述：
- 项目背景：客户需求来源、行业背景
- 项目目标：本次检测系统的核心目标
- 项目范围：系统覆盖的检测内容

2. 需求分析：
- 功能需求：需要检测的缺陷类型、检测方式
- 性能指标：检测精度、产能要求、误检率
- 约束条件：安装空间、环境要求、预算限制

3. 系统方案设计：
- 硬件方案：相机、镜头、光源、工控配置
- 算法方案：采用的技术路线、检测流程
- 系统架构：整体架构、数据流程

4. 检测流程说明：
- 检测流程描述
- 各环节说明
- 异常处理机制

5. BOM清单与成本估算：
- 设备清单表格
- 成本分类汇总
- 总报价

6. 项目计划：
- 各阶段工作内容和周期
- 交付物

7. 风险评估与应对：
- 风险项、影响程度、应对措施

8. 验收标准：
- 检测精度、系统稳定性等指标

9. 售后服务：
- 质保期、响应时间、培训安排

输出格式：
请返回JSON格式的报告内容，包含：
- report_meta: 报告元数据
- sections: 各章节内容
- full_markdown: 完整的Markdown格式报告
"""


@tool
def report_generation(project_data: str, report_format: str = "markdown", include_cost: bool = True, include_timeline: bool = True) -> str:
    """
    方案报告生成工具 - 根据项目数据生成完整的专业方案报告。

    Args:
        project_data: 项目数据（包含检测需求、硬件选型、算法方案等结构化信息）
        report_format: 报告格式（markdown/html/pdf），默认markdown
        include_cost: 是否包含成本估算，默认True
        include_timeline: 是否包含项目时间表，默认True

    Returns:
        结构化的方案报告（JSON格式）
    """
    ctx = request_context.get() or new_context(method="report_generation")

    try:
        client = LLMClient(ctx=ctx)

        prompt = f"""请根据以下项目数据生成完整的专业方案报告：

项目数据：
{project_data}

报告格式：{report_format}
是否包含成本估算：{include_cost}
是否包含项目时间表：{include_timeline}

请生成一份完整、专业、可直接提交给客户的项目方案报告。"""

        response = client.invoke(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="mimo-v2.5",
            temperature=0.4,
            max_completion_tokens=10000
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
            "raw_content": project_data
        }, ensure_ascii=False, indent=2)
