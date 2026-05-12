"""
需求分析工具
根据产品尺寸、检测精度、TT耗时等参数，评估最优硬件选型方案
"""

from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


@tool
def analyze_requirement(
    product_name: str,
    product_size_mm: str,
    defect_type: str,
    defect_size_mm: float,
    tt_seconds: float,
    daily_output: int = 10000
) -> str:
    """
    分析检测需求，评估硬件选型方案。
    
    参数:
        product_name: 产品名称（如"液晶显示屏"、"PCB板"等）
        product_size_mm: 产品尺寸，格式"长×宽"（单位mm），如"208×195"
        defect_type: 缺陷类型（如"气泡"、"划伤"、"异物"、"裂纹"等）
        defect_size_mm: 最小缺陷尺寸（单位mm），如0.1表示0.1mm的缺陷需要被检出
        tt_seconds: 检测节拍时间（单位秒），表示检测完一个产品需要的时间
        daily_output: 日产能（默认10000），用于计算工作负载
    
    返回:
        包含完整需求评估和硬件选型建议的字符串
    """
    ctx = request_context.get() or new_context(method="analyze_requirement")
    
    # 解析产品尺寸
    try:
        dimensions = product_size_mm.split("×")
        length_mm = float(dimensions[0])
        width_mm = float(dimensions[1])
    except:
        return f"错误：产品尺寸格式不正确，请使用'长×宽'格式，如'208×195'"
    
    # 计算像素当量
    # 安全系数2.0：像素当量 × 2 ≤ 最小缺陷尺寸
    # 因此：像素当量 ≤ 缺陷尺寸 / 2
    max_pixel_size = defect_size_mm / 2.0
    
    # 计算所需分辨率（取长边计算）
    max_dimension = max(length_mm, width_mm)
    required_pixels = max_dimension / max_pixel_size
    
    # 向上取整到标准分辨率
    standard_resolutions = [2048, 2448, 4096, 5472, 8192, 16384, 32000]
    selected_resolution = 2048
    for res in standard_resolutions:
        if res >= required_pixels:
            selected_resolution = res
            break
    
    # 计算像素当量
    actual_pixel_size = max_dimension / selected_resolution
    
    # 判断相机类型
    # 规则：TT<5秒 或 分辨率>8000像素 → 线扫描相机
    # 规则：TT>=5秒 或 分辨率<=8000像素 → 面阵相机
    if tt_seconds < 5 or selected_resolution >= 8000:
        camera_type = "线扫描相机"
        camera_reasons = [
            f"TT={tt_seconds}秒<5秒，需要高速检测" if tt_seconds < 5 else "",
            f"分辨率{selected_resolution}≥8K" if selected_resolution >= 8000 else ""
        ]
        camera_reasons = [r for r in camera_reasons if r]
    else:
        camera_type = "面阵相机"
        camera_reasons = [
            f"TT={tt_seconds}秒≥5秒，速度要求适中",
            f"分辨率{selected_resolution}≤8K"
        ]
    
    # 光源选型（根据缺陷类型）
    lighting_options = {
        "气泡": "同轴光源 + 背光源组合（高透光检测）",
        "划伤": "低角度环形光源（强调边缘阴影）",
        "异物": "同轴光源 或 条形光源（均匀照明）",
        "裂纹": "背光源（高对比度轮廓）",
        "脏污": "同轴光源 或 低角度光（去除反光）",
        "崩边": "背光源（轮廓清晰）"
    }
    lighting = lighting_options.get(defect_type, "同轴光源（通用）")
    
    # 工控机配置（基于华星标准）
    if selected_resolution >= 16000:
        ipc_config = "高配标准"
        ipc_spec = "i9-13900K + RTX 4090 + 64GB + 20TB"
        ipc_price = "35000-40000元"
    elif selected_resolution >= 8000:
        ipc_config = "中配标准"
        ipc_spec = "i9-13900K + RTX 4070Ti + 32GB + 4TB"
        ipc_price = "25000-35000元"
    else:
        ipc_config = "中配标准"
        ipc_spec = "i7-12700K + RTX 4060 + 32GB + 2TB"
        ipc_price = "15000-25000元"
    
    # 计算日处理量
    daily_processing = daily_output
    peak_hourly = int(daily_output / 10)  # 假设10小时工作制
    
    # 构建评估报告
    report = f"""
# 需求评估报告

## 1. 基础信息
| 项目 | 参数 |
|------|------|
| 产品名称 | {product_name} |
| 产品尺寸 | {length_mm}mm × {width_mm}mm |
| 检测类型 | {defect_type} |
| 最小检出尺寸 | {defect_size_mm}mm |
| 检测节拍(TT) | {tt_seconds}秒/件 |
| 日产能 | {daily_output}件 |

## 2. 技术参数计算
| 项目 | 计算值 | 说明 |
|------|--------|------|
| 最大尺寸边长 | {max_dimension}mm | 取长宽最大值 |
| 像素当量要求 | ≤{max_pixel_size:.4f}mm/pixel | 安全系数2.0 |
| 理论所需像素 | {required_pixels:.0f}pixel | 基于精度要求 |
| 实际像素当量 | {actual_pixel_size:.4f}mm/pixel | 使用{selected_resolution}像素 |
| 可检出最小缺陷 | {actual_pixel_size * 2:.4f}mm | 2倍像素当量 |

## 3. 硬件选型建议

### 3.1 相机选型
**推荐类型**: {camera_type}
**推荐分辨率**: {selected_resolution}像素
**选择理由**:
"""
    for reason in camera_reasons:
        report += f"  - {reason}\n"
    
    report += f"""
### 3.2 光源选型
**推荐类型**: {lighting}
**说明**: 根据{defect_type}检测特点选择

### 3.3 工控机配置
**配置级别**: {ipc_config}
**推荐配置**: {ipc_spec}
**参考价格**: {ipc_price}

## 4. 检测能力评估
| 指标 | 目标值 | 说明 |
|------|--------|------|
| 漏检率 | <0.5% | 基于华星RFQ标准 |
| 误检率 | <1-2% | 基于华星RFQ标准 |
| 检测速度 | ≤{tt_seconds}秒/件 | 满足TT要求 |
| 日处理量 | {daily_processing}件 | 满足产能要求 |

## 5. 成本估算
| 项目 | 估算价格 |
|------|----------|
| 线扫描相机({selected_resolution}K) | 8000-30000元 |
| 镜头+光源 | 5000-20000元 |
| 工控机({ipc_config}) | {ipc_price} |
| 其他配件 | 5000-10000元 |
| **总计** | **约45000-90000元** |

## 6. 实施建议
1. 建议先进行样品测试，验证像素当量配置是否满足检出要求
2. 如检测速度无法满足TT，考虑使用GPU加速或增加工控机数量
3. 气泡检测建议使用同轴+背光组合，提高透光缺陷对比度
"""
    
    return report


@tool
def calculate_block_strategy(
    image_width: int,
    image_height: int,
    max_memory_mb: int = 4000,
    overlap_pixels: int = 300
) -> str:
    """
    计算大图分块处理策略。
    
    参数:
        image_width: 图像宽度（像素）
        image_height: 图像高度（像素）
        max_memory_mb: 最大内存占用（MB），默认4000MB
        overlap_pixels: 分块重叠像素，默认300
    
    返回:
        分块策略配置和代码示例
    """
    ctx = request_context.get() or new_context(method="calculate_block_strategy")
    
    # 计算单像素内存占用（RGB 3字节 + 浮点中间结果）
    bytes_per_pixel = 12  # 3(RGB) + 9(浮点计算)
    max_bytes = max_memory_mb * 1024 * 1024
    
    # 计算理想块大小
    # 保持宽高比，宽度方向优先
    aspect_ratio = image_width / image_height
    
    # 面积反推
    ideal_area = max_bytes / bytes_per_pixel
    ideal_height = int((ideal_area / aspect_ratio) ** 0.5)
    ideal_width = int(ideal_height * aspect_ratio)
    
    # 对齐到偶数
    ideal_width = (ideal_width // 2) * 2
    ideal_height = (ideal_height // 2) * 2
    
    # 确保不超过图像尺寸
    block_width = min(ideal_width, image_width)
    block_height = min(ideal_height, image_height)
    
    # 计算分块数量
    cols = (image_width - overlap_pixels) // (block_width - overlap_pixels) + 1
    rows = (image_height - overlap_pixels) // (block_height - overlap_pixels) + 1
    total_blocks = cols * rows
    
    # 生成代码模板
    code_template = f'''"""
{image_width}×{image_height}大图分块处理策略
自动计算分块数量: {total_blocks}块 ({rows}行×{cols}列)
"""

from concurrent.futures import ThreadPoolExecutor
import numpy as np

# 分块配置
BLOCK_WIDTH = {block_width}
BLOCK_HEIGHT = {block_height}
OVERLAP = {overlap_pixels}
IMAGE_WIDTH = {image_width}
IMAGE_HEIGHT = {image_height}

# 计算分块起止坐标
def get_chunk_bounds():
    chunks = []
    for row in range({rows}):
        for col in range({cols}):
            start_x = col * (BLOCK_WIDTH - OVERLAP)
            start_y = row * (BLOCK_HEIGHT - OVERLAP)
            end_x = min(start_x + BLOCK_WIDTH, IMAGE_WIDTH)
            end_y = min(start_y + BLOCK_HEIGHT, IMAGE_HEIGHT)
            
            # 修正最后一块的起点（确保覆盖完整）
            if col == {cols - 1}:
                start_x = IMAGE_WIDTH - BLOCK_WIDTH
                end_x = IMAGE_WIDTH
            if row == {rows - 1}:
                start_y = IMAGE_HEIGHT - BLOCK_HEIGHT
                end_y = IMAGE_HEIGHT
            
            chunks.append({{
                "index": row * {cols} + col,
                "start_x": max(0, start_x),
                "start_y": max(0, start_y),
                "end_x": end_x,
                "end_y": end_y,
                "width": end_x - max(0, start_x),
                "height": end_y - max(0, start_y)
            }})
    return chunks

# 多线程并行处理
def process_chunks_parallel(image, chunks, process_func, max_workers=8):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for chunk in chunks:
            # 提取块图像
            chunk_img = image[chunk["start_y"]:chunk["end_y"], 
                           chunk["start_x"]:chunk["end_x"]]
            future = executor.submit(process_func, chunk_img, chunk)
            futures.append((future, chunk))
        
        for future, chunk in futures:
            result = future.result()
            results.append(result)
    
    return results

# IOU去重合并结果
def merge_results(results, iou_threshold=0.3):
    merged = []
    for result in results:
        for box in result:
            keep = True
            for existing in merged:
                iou = calculate_iou(box, existing)
                if iou > iou_threshold:
                    keep = False
                    break
            if keep:
                merged.append(box)
    return merged

def calculate_iou(box1, box2):
    x1 = max(box1["x"], box2["x"])
    y1 = max(box1["y"], box2["y"])
    x2 = min(box1["x"] + box1["w"], box2["x"] + box2["w"])
    y2 = min(box1["y"] + box1["h"], box2["y"] + box2["h"])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = box1["w"] * box1["h"]
    box2_area = box2["w"] * box2["h"]
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0
'''
    
    return f"""# 大图分块策略配置

## 图像信息
- 原始尺寸: {image_width} × {image_height} 像素
- 内存占用: 约 {image_width * image_height * 3 / 1024 / 1024:.1f} MB

## 分块配置
- 块尺寸: {block_width} × {block_height} 像素
- 重叠区域: {overlap_pixels} 像素
- 分块数量: {total_blocks} 块 ({rows}行 × {cols}列)
- 内存估算: 约 {block_width * block_height * bytes_per_pixel / 1024 / 1024:.1f} MB/块

## 代码实现

```python
{code_template}
```

## 使用示例

```python
# 1. 获取分块坐标
chunks = get_chunk_bounds()

# 2. 定义处理函数（气泡检测示例）
def detect_bubbles(chunk_img, chunk_info):
    # 使用Vap SDK处理
    from Vap.Algo.Badt.Fi import BubbleDetect as bd
    result = bd.process(chunk_img)
    
    # 坐标修正（加上块起点坐标）
    for defect in result.defects:
        defect["x"] += chunk_info["start_x"]
        defect["y"] += chunk_info["start_y"]
    return result.defects

# 3. 并行处理
results = process_chunks_parallel(image, chunks, detect_bubbles, max_workers=8)

# 4. 合并结果
final_results = merge_results(results, iou_threshold=0.3)
```
"""
