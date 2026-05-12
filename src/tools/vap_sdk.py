"""
Vap.Algo.Badt.Fi SDK 代码生成工具
用于生成调用 Vap 工业视觉检测库的完整代码模板
"""
import os
import json
from datetime import datetime
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


# Vap SDK 算法模块映射
ALGO_MODULE_MAP = {
    "PROTECTIVE_FILM_DEFECT": {
        "name": "保护膜不良缺陷检测",
        "namespace": "DetectProtectiveFilm",
        "defects": ["气泡", "异物", "翘起", "残胶", "污渍", "划伤"],
        "default_params": {
            "IsCheckBubble": True,
            "BubbleConfTh": 0.25,
            "BubbleWidthTh": 10,
            "BubbleHeightTh": 10,
            "CropSize": 1280,
            "Overlap": 40
        }
    },
    "FPC_PCB_DEFECT": {
        "name": "FPC/PCB类缺陷检测",
        "namespace": "DetectFpcPcb",
        "defects": ["划伤", "漏铜", "元器件缺失"],
        "default_params": {}
    },
    "POL_DEFECT": {
        "name": "POL类不良缺陷检测",
        "namespace": "DetectPol",
        "defects": ["凹痕", "凸点", "翘起", "错位"],
        "default_params": {}
    },
    "TAPE_DEFECT": {
        "name": "Tape不良缺陷检测",
        "namespace": "DetectTap",
        "defects": ["凸起", "褶皱", "open", "翘起", "磨白", "破损"],
        "default_params": {}
    },
    "PULL_TAB_DEFECT": {
        "name": "易撕贴缺陷检测",
        "namespace": "DetectPullTab",
        "defects": ["偏位"],
        "default_params": {}
    },
    "PANEL_DAMAGE_DEFECT": {
        "name": "破损（Panel）缺陷检测",
        "namespace": "DetectPanelDamage",
        "defects": ["裂纹", "边崩裂", "角崩裂", "毛刺"],
        "default_params": {}
    },
    "ADHESIVE_RESIDUE_DEFECT": {
        "name": "胶类不良缺陷检测",
        "namespace": "DetectAdhesiveResidue",
        "defects": ["正胶/背胶", "溢胶", "UV胶", "Tuffy胶"],
        "default_params": {}
    },
    "COVER_GLASS_DEFECT": {
        "name": "CG盖板类缺陷检测",
        "namespace": "DetectCoverGlass",
        "defects": ["异物", "划伤", "崩裂", "污渍"],
        "default_params": {}
    },
    "BACKLIGHT_DEFECT": {
        "name": "背光类不良缺陷检测",
        "namespace": "DetectBacklight",
        "defects": ["B/L异物", "柱脚不良", "污渍", "压痕", "掉漆", "凹凸点", "异色"],
        "default_params": {}
    }
}


@tool
def vap_code_generation(
    detection_task: str,
    algorithm_module: str = "PROTECTIVE_FILM_DEFECT",
    image_resolution: str = "16K*500",
    resolution_um: float = 15.0,
    enable_roi: bool = False,
    crop_size: int = 1280,
    overlap: int = 40
) -> str:
    """
    【核心工具】生成调用 Vap.Algo.Badt.Fi SDK 进行工业视觉检测的完整C#代码模板。
    
    ★★★ 重要：优先使用此工具生成Vap SDK代码，除非用户明确指定使用其他SDK ★★★
    
    支持的算法模块：
    - PROTECTIVE_FILM_DEFECT: 保护膜缺陷检测（气泡、异物、翘起、残胶、污渍、划伤）
    - FPC_PCB_DEFECT: FPC/PCB缺陷检测（划伤、漏铜、元器件缺失）
    - POL_DEFECT: POL缺陷检测（凹痕、凸点、翘起、错位）
    - TAPE_DEFECT: Tape缺陷检测（凸起、褶皱、open、翘起）
    - COVER_GLASS_DEFECT: 盖板玻璃缺陷检测
    - BACKLIGHT_DEFECT: 背光缺陷检测
    
    Args:
        detection_task: 检测任务描述，如"液晶显示屏气泡检测"
        algorithm_module: 算法模块名称
        image_resolution: 输入图像分辨率，如"16K*500"、"8192*4096"
        resolution_um: 相机分辨率(um/pixel)，默认15.0
        enable_roi: 是否启用ROI区域检测
        crop_size: 大图裁切尺寸(px)，默认1280，用于分块推理超大图像
        overlap: 裁切重叠尺寸(px)，默认40，防止边缘缺陷漏检

    Returns:
        包含完整C#代码模板的JSON字符串
    """
    ctx = request_context.get() or new_context(method="vap_code_generation")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    algo_info = ALGO_MODULE_MAP.get(algorithm_module, ALGO_MODULE_MAP["PROTECTIVE_FILM_DEFECT"])
    namespace = algo_info["namespace"]

    # 生成代码
    code_template = f'''// Vap.Algo.Badt.Fi SDK 检测代码模板
// 生成时间: {timestamp}
// 算法模块: {algo_info["name"]}
// 检测任务: {detection_task}
// 输入分辨率: {image_resolution}

using HalconDotNet;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reflection;
using Vap.Algo.Badt.Fi.Attributes;
using Vap.Algo.Badt.Fi.Base;
using Vap.Algo.Badt.Fi.Common;
using VAP = Vap.Algo.Badt.Fi.{namespace};

namespace VisionInspection
{{
    public class InspectionRunner
    {{
        private VAP.InspectionAlgo _algo;
        private VAP.InspectionParam _param;
        private ILogger<InspectionRunner> _logger;

        /// <summary>
        /// 初始化检测器
        /// </summary>
        /// <param name="modelPath">AI模型JSON配置文件路径</param>
        /// <param name="resolutionX">相机X方向分辨率(um/pixel)</param>
        /// <param name="resolutionY">相机Y方向分辨率(um/pixel)</param>
        public void Initialize(string modelPath, double resolutionX = {resolution_um}, double resolutionY = {resolution_um})
        {{
            // 构造日志工厂
            using var loggerFactory = LoggerFactory.Create(b =>
            {{
                b.SetMinimumLevel(LogLevel.Debug);
                b.AddConsole();
            }});
            _logger = loggerFactory.CreateLogger<InspectionRunner>();

            // 构造参数
            _param = new VAP.InspectionParam
            {{
                ModelPath = modelPath,
                ResolutionX = resolutionX,
                ResolutionY = resolutionY,
                EnableDetect = true,
                CropSize = {crop_size},       // 裁切尺寸，防止超大图像OOM
                Overlap = {overlap},          // 重叠尺寸，防止边缘缺陷漏检
                // 以下为{algo_info["name"]}专属参数
                BubbleConfTh = 0.25,          // 置信度阈值
                BubbleWidthTh = 10,            // 宽度阈值(px)
                BubbleHeightTh = 10,           // 高度阈值(px)
                IsCheckBubble = true,         // 是否检测气泡
                MergeIoUTh = 0,               // 合并IoU阈值，0表示任意相交即合并
            }};

            // 创建算法实例并初始化
            _algo = new VAP.InspectionAlgo(_logger);
            _algo.Init(_param);
            _logger.LogInformation("Vap SDK 初始化成功，模型: {{ModelPath}}", modelPath);
        }}

        /// <summary>
        /// 执行缺陷检测
        /// </summary>
        /// <param name="imagePath">输入图像路径</param>
        /// <param name="roiRect">ROI区域(可选)，格式: LeftTopX,LeftTopY,RightBottomX,RightBottomY</param>
        /// <returns>检测结果，包含缺陷列表和尺寸(mm)</returns>
        public InspectionResult RunDetection(string imagePath, string roiRect = null)
        {{
            var result = new InspectionResult();

            try
            {{
                // 1. 读取HALCON图像
                HOperatorSet.ReadImage(out HObject hImage, imagePath);
                HOperatorSet.GetImageSize(hImage, out HTuple width, out HTuple height);
                _logger.LogInformation("加载图像: {{Path}}, 尺寸: {{Width}}x{{Height}}", 
                    imagePath, width, height);

                // 2. 构造输入
                using var input = new VAP.InspectionInput {{ SrcImg = hImage }};

                // 3. 设置ROI(可选)
                if (!string.IsNullOrEmpty(roiRect))
                {{
                    var parts = roiRect.Split(',');
                    if (parts.Length == 4)
                    {{
                        input.RoiRect = new ROIRect
                        {{
                            LeftTopX = double.Parse(parts[0]),
                            LeftTopY = double.Parse(parts[1]),
                            RightBottomX = double.Parse(parts[2]),
                            RightBottomY = double.Parse(parts[3])
                        }};
                        _logger.LogInformation("设置ROI: {{ROI}}", roiRect);
                    }}
                }}

                // 4. 执行检测
                var ret = _algo.Run(input, _param, out VAP.InspectionResult algoResult);

                // 5. 处理结果
                result.ReturnType = ret.ToString();
                result.TotalDefects = algoResult.Defects?.Count ?? 0;
                result.IsOK = ret == RESULT_TYPE.OK;

                foreach (var defect in algoResult.Defects ?? new List<SingleDefect>())
                {{
                    // 获取缺陷类型中文名
                    var defectName = GetDefectTypeName(defect.DefectType);

                    result.Defects.Add(new DefectInfo
                    {{
                        Type = defectName,
                        Confidence = defect.DefectConf,
                        Rect = defect.DefectRect,
                        WidthMm = defect.DefectWidth,
                        HeightMm = defect.DefectHeight,
                        LengthMm = defect.Length
                    }});

                    _logger.LogWarning("检测到缺陷: {{Type}} 置信度:{{Conf:F2}} 尺寸:{{Width:F2}}x{{Height:F2}}mm 位置:[{{X1}},{{Y1}}~{{X2}},{{Y2}}]",
                        defectName, defect.DefectConf, defect.DefectWidth, defect.DefectHeight,
                        defect.DefectRect.LeftTopX, defect.DefectRect.LeftTopY,
                        defect.DefectRect.RightBottomX, defect.DefectRect.RightBottomY);
                }}

                if (ret == RESULT_TYPE.ERROR)
                {{
                    result.ErrorMessage = algoResult.ErrMsg;
                    _logger.LogError("检测失败: {{Error}}", algoResult.ErrMsg);
                }}
            }}
            catch (Exception ex)
            {{
                result.ReturnType = "ERROR";
                result.ErrorMessage = ex.Message;
                _logger.LogError(ex, "检测异常");
            }}

            return result;
        }}

        /// <summary>
        /// 批量处理图像目录
        /// </summary>
        public List<BatchResult> BatchProcess(string imageDir, string imagePattern = "*.bmp")
        {{
            var batchResults = new List<BatchResult>();
            var imageFiles = Directory.GetFiles(imageDir, imagePattern);

            foreach (var imageFile in imageFiles)
            {{
                var result = RunDetection(imageFile);
                batchResults.Add(new BatchResult
                {{
                    ImagePath = imageFile,
                    Result = result
                }});
            }}

            _logger.LogInformation("批量处理完成: {{Total}}张, OK:{{OK}}, NG:{{NG}}",
                batchResults.Count, batchResults.Count(r => r.Result.IsOK), batchResults.Count(r => !r.Result.IsOK));

            return batchResults;
        }}

        /// <summary>
        /// 释放资源
        /// </summary>
        public void Dispose()
        {{
            _algo?.Dispose();
            _logger?.LogInformation("资源已释放");
        }}

        private string GetDefectTypeName(DefectType type)
        {{
            return typeof(DefectType)
                .GetField(type.ToString())
                ?.GetCustomAttribute<DescriptionAttribute>()
                ?.Description ?? type.ToString();
        }}
    }}

    public class InspectionResult
    {{
        public string ReturnType {{ get; set; }}
        public bool IsOK {{ get; set; }}
        public int TotalDefects {{ get; set; }}
        public string ErrorMessage {{ get; set; }}
        public List<DefectInfo> Defects {{ get; set; }} = new List<DefectInfo>();
    }}

    public class DefectInfo
    {{
        public string Type {{ get; set; }}
        public double Confidence {{ get; set; }}
        public NRect Rect {{ get; set; }}
        public double WidthMm {{ get; set; }}
        public double HeightMm {{ get; set; }}
        public double LengthMm {{ get; set; }}
    }}

    public class BatchResult
    {{
        public string ImagePath {{ get; set; }}
        public InspectionResult Result {{ get; set; }}
    }}
}}
'''

    # 项目文件配置
    csproj_content = f'''<!-- VapSDK.InspDemo.csproj -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <!-- Vap.Algo.Badt.Fi 核心库 -->
    <Reference Include="Vap.Algo.Badt.Fi">
      <HintPath>bin/Vap.Algo.Badt.Fi.dll</HintPath>
    </Reference>
    <!-- HALCON 视觉库 -->
    <Reference Include="halcondotnetxl">
      <HintPath>bin/halcondotnetxl.dll</HintPath>
    </Reference>
    <!-- 日志组件 -->
    <PackageReference Include="Microsoft.Extensions.Logging" Version="6.0.0" />
    <PackageReference Include="Microsoft.Extensions.Logging.Console" Version="6.0.0" />
    <!-- 属性通知(用于参数编辑器) -->
    <PackageReference Include="PropertyChanged.Fody" Version="4.1.0" />
  </ItemGroup>
</Project>
'''

    # 模型配置文件示例
    model_config = f'''{{
  "model_name": "{detection_task.replace(" ", "_")}_detector",
  "model_path": "./models/detector.h5",
  "input_size": [1280, 1280],
  "confidence_threshold": 0.25,
  "nms_threshold": 0.45,
  "classes": ["bubble", "scratch", "stain"],
  "preprocess": {{
    "normalize": true,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225]
  }},
  "postprocess": {{
    "min_area_px": 100,
    "merge_iou_threshold": 0.0
  }}
}}
'''

    # 使用示例
    usage_example = f'''// Program.cs - 使用示例
using VisionInspection;

// 创建检测器
var runner = new InspectionRunner();

// 初始化(加载模型)
runner.Initialize(
    modelPath: @"D:\\models\\{detection_task.replace(" ", "_")}.json",
    resolutionX: {resolution_um},  // um/pixel
    resolutionY: {resolution_um}
);

// 单张图像检测
var result = runner.RunDetection(@"D:\\images\\sample.bmp");
Console.WriteLine($"检测结果: {{result.ReturnType}}, 缺陷数: {{result.TotalDefects}}");

// 批量处理
var batchResults = runner.BatchProcess(@"D:\\images\\", "*.bmp");

// 释放资源
runner.Dispose();
'''

    return json.dumps({
        "status": "success",
        "algorithm_module": algorithm_module,
        "module_name": algo_info["name"],
        "namespace": namespace,
        "supported_defects": algo_info["defects"],
        "image_resolution": image_resolution,
        "resolution_um": resolution_um,
        "crop_size": crop_size,
        "overlap": overlap,
        "timestamp": timestamp,
        "files": {
            "InspectionRunner.cs": code_template.strip(),
            "VapSDK.InspDemo.csproj": csproj_content.strip(),
            "model_config.json": model_config.strip(),
            "Program.cs": usage_example.strip()
        }
    }, ensure_ascii=False, indent=2)


@tool
def vap_module_info() -> str:
    """
    查询 Vap.Algo.Badt.Fi SDK 支持的所有算法模块信息。

    Returns:
        包含所有算法模块及其参数说明的JSON字符串
    """
    modules_info = {}
    for key, info in ALGO_MODULE_MAP.items():
        modules_info[key] = {
            "name": info["name"],
            "namespace": info["namespace"],
            "supported_defects": info["defects"],
            "parameters": {
                "common": {
                    "ModelPath": {"type": "string", "default": "", "desc": "AI模型JSON配置文件路径"},
                    "ResolutionX": {"type": "double", "default": "15.0", "desc": "相机X分辨率(um/pixel)"},
                    "ResolutionY": {"type": "double", "default": "15.0", "desc": "相机Y分辨率(um/pixel)"},
                    "EnableDetect": {"type": "bool", "default": "true", "desc": "算法总开关"},
                    "CropSize": {"type": "int", "default": "1280", "desc": "大图裁切尺寸(px)"},
                    "Overlap": {"type": "int", "default": "40", "desc": "裁切重叠尺寸(px)"}
                },
                "protective_film": {
                    "IsCheckBubble": {"type": "bool", "default": "true", "desc": "是否检测气泡"},
                    "BubbleConfTh": {"type": "double", "default": "0.25", "desc": "气泡置信度阈值[0,1]"},
                    "BubbleWidthTh": {"type": "int", "default": "10", "desc": "气泡宽度阈值(px)"},
                    "BubbleHeightTh": {"type": "int", "default": "10", "desc": "气泡高度阈值(px)"},
                    "MergeIoUTh": {"type": "double", "default": "0", "desc": "合并IoU阈值[0,1]"}
                }
            }
        }

    return json.dumps({
        "status": "success",
        "total_modules": len(ALGO_MODULE_MAP),
        "modules": modules_info,
        "usage_guide": "使用 vap_code_generation 工具生成具体算法的代码模板"
    }, ensure_ascii=False, indent=2)


@tool
def vap_deployment_guide() -> str:
    """
    获取 Vap.Algo.Badt.Fi SDK 的部署指南和常见问题解答。

    Returns:
        包含部署指南和FAQ的JSON字符串
    """
    guide = {
        "deployment_steps": [
            {
                "step": 1,
                "title": "安装依赖",
                "content": "1. 安装 HALCON 21.5 或更高版本\n2. 添加 Vap.Algo.Badt.Fi.dll 引用\n3. 安装 NuGet 包: Microsoft.Extensions.Logging"
            },
            {
                "step": 2,
                "title": "准备模型文件",
                "content": "1. 获取训练好的 AI 模型(.h5/.onnx)\n2. 准备模型配置文件(model.json)\n3. 将模型文件放置在部署目录的 models/ 子目录下"
            },
            {
                "step": 3,
                "title": "配置参数",
                "content": "1. 设置 CropSize: 根据图像尺寸设置裁切大小\n2. 设置 Overlap: 防止边缘缺陷漏检，建议40-80px\n3. 调整置信度阈值: BubbleConfTh 等参数"
            },
            {
                "step": 4,
                "title": "集成到产线",
                "content": "1. 使用工业相机采集图像\n2. 调用 InspectionRunner.RunDetection()\n3. 根据返回值判断OK/NG\n4. 发送结果到PLC/MES系统"
            }
        ],
        "common_issues": [
            {
                "issue": "模型文件不存在",
                "solution": "检查 ModelPath 路径是否正确，确保文件存在于指定位置"
            },
            {
                "issue": "HALCON图像为空",
                "solution": "检查相机连接和图像采集代码，确保图像成功获取"
            },
            {
                "issue": "内存溢出(OOM)",
                "solution": "减小 CropSize 参数，建议1280-2560；或升级GPU显存"
            },
            {
                "issue": "检测结果为空",
                "solution": "降低置信度阈值(BubbleConfTh)；检查ROI区域是否设置正确"
            }
        ],
        "performance_tips": [
            "使用Async推理模式提升吞吐量",
            "合理设置CropSize，避免过大导致OOM",
            "使用ROI排除背景区域，减少无效计算",
            "批量处理时使用线程池并行"
        ]
    }

    return json.dumps({
        "status": "success",
        "guide": guide,
        "sdk_version": "Vap.Algo.Badt.Fi v1.0",
        "target_framework": "netstandard2.1 / .NET 6.0+",
        "dependencies": ["HalconDotNet 21.5+", "Microsoft.Extensions.Logging.Abstractions"]
    }, ensure_ascii=False, indent=2)
