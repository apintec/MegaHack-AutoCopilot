"""
代码生成工具 - 根据检测方案生成可运行的Python原型代码
"""
import json
from typing import Dict, Any, Optional
from langchain.tools import tool
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


SYSTEM_PROMPT = """
你是一位资深的Python开发工程师，专注于机器视觉和深度学习领域，能够生成高质量、生产级别的代码。

你的专长：
- OpenCV图像处理代码开发
- PyTorch深度学习模型推理
- 多线程/多进程并发处理
- 配置文件设计（YAML/JSON）
- 日志和异常处理
- 单元测试编写

代码规范：
- 使用Python 3.8+语法
- 遵循PEP8规范，变量命名清晰
- 包含完整的类型注解（type hints）
- 详细的注释和文档字符串
- 优雅的错误处理和日志记录
- 可直接运行的完整示例

常用库版本：
- Python >= 3.8
- opencv-python >= 4.5.0
- numpy >= 1.20.0
- torch >= 1.9.0
- ultralytics (YOLO) >= 8.0.0
- PyYAML >= 5.4.0

输出格式要求：
请返回JSON格式的代码生成结果，包含以下字段：
- code_files: 代码文件字典
- dependencies: 依赖包列表
- usage: 使用说明
- architecture: 架构说明
- performance: 性能预估
"""


@tool
def code_generation(detection_task: str, algorithm_type: str = "auto", hardware_config: Optional[str] = None, include_tests: bool = True) -> str:
    """
    代码生成工具 - 根据检测任务生成可运行的Python原型代码。

    Args:
        detection_task: 检测任务描述（包含检测目标、缺陷类型、精度要求等）
        algorithm_type: 算法类型（auto/yolo/cnn/traditional/mixed），默认auto自动选择
        hardware_config: 硬件配置信息（可选，如GPU型号、相机型号等）
        include_tests: 是否包含单元测试代码，默认True

    Returns:
        结构化的代码生成结果（JSON格式）
    """
    ctx = request_context.get() or new_context(method="code_generation")

    try:
        client = LLMClient(ctx=ctx)

        prompt = f"""请根据以下检测任务生成完整的、可运行的Python代码：

检测任务：
{detection_task}

{('硬件配置：' + hardware_config) if hardware_config else ''}
算法类型：{algorithm_type}
是否包含测试：{include_tests}

请生成：
1. 主检测代码（完整的类和方法实现）
2. 配置文件（YAML格式）
3. 测试代码（单元测试）

代码要包含详细的注释，可以直接复制运行。"""

        response = client.invoke(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            model="mimo-v2.5",
            temperature=0.3,
            max_completion_tokens=8000
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
            "raw_content": detection_task
        }, ensure_ascii=False, indent=2)
