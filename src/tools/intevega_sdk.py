"""
InteVega AI SDK 代码生成工具
用于生成调用 InteVega 推理库的完整代码模板
"""
import os
import json
from datetime import datetime
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


# C#代码模板 (大括号已转义)
CSHARP_CODE_TEMPLATE = '''
// InteVega AI SDK {algorithm_type} 推理代码模板
// 生成时间: {timestamp}
// 算法类型: {algorithm_name}
// 适用场景: {use_case}

using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using OpenCvSharp;

namespace InteVegaInference
{{
    public class {class_name}
    {{
        // SDK DLL 导入
        [DllImport("lib_common.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern int mallocImgBufferOnCUDA(ref IntPtr gpuImgBuffer, int iMaxBufferSize);
        
        [DllImport("lib_common.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern int copyImgBufferFromCpuToGpu(IntPtr cpuBuffer, int maxBufferSize, 
            int width, int height, int channels, int stride, ref IntPtr gpuBuffer);
        
        [DllImport("lib_common.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern int freeImgBufferOnCUDA(IntPtr gpuBuffer);
        
        // 模型相关导入
        [DllImport("lib_detector.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern int CreateDetectorHandle(string configPath, ref IntPtr handle);
        
        [DllImport("lib_detector.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern int DetectorInference(IntPtr handle, ref TImageInfo input, 
            ref TDetectorOutput output);
        
        [DllImport("lib_detector.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern int DestroyDetectorHandle(IntPtr handle);
        
        private IntPtr _gpuBuffer;
        private int _maxBufferSize;
        private IntPtr _detectorHandle;
        
        /// <summary>初始化推理引擎</summary>
        public bool Initialize(string configPath, int imageWidth = 8192, int imageHeight = 8192)
        {{
            try
            {{
                _maxBufferSize = imageWidth * imageHeight * 3;
                int hr = mallocImgBufferOnCUDA(ref _gpuBuffer, _maxBufferSize);
                if (hr != 0) throw new Exception("GPU显存申请失败: " + hr);
                
                hr = CreateDetectorHandle(configPath, ref _detectorHandle);
                if (hr != 0) throw new Exception("创建推理句柄失败: " + hr);
                
                Console.WriteLine("InteVega SDK 初始化成功");
                return true;
            }}
            catch (Exception ex)
            {{
                Console.WriteLine("初始化失败: " + ex.Message);
                return false;
            }}
        }}
        
        /// <summary>执行缺陷检测推理</summary>
        public List<DefectResult> Detect(string imagePath, List<Rect> roiRegions = null)
        {{
            var results = new List<DefectResult>();
            try
            {{
                using var srcMat = Cv2.ImRead(imagePath, ImreadModes.Color);
                if (srcMat.Empty()) throw new Exception("图像加载失败");
                
                var imgInfo = PrepareImageInfo(srcMat, _gpuBuffer, _maxBufferSize);
                
                if (roiRegions != null && roiRegions.Count > 0)
                {{
                    imgInfo.nROINum = roiRegions.Count;
                    imgInfo.ROIInfo = Marshal.AllocHGlobal(Marshal.SizeOf<TBbox>() * roiRegions.Count);
                    
                    for (int i = 0; i < roiRegions.Count; i++)
                    {{
                        var bbox = new TBbox {{ x = roiRegions[i].X, y = roiRegions[i].Y, 
                            w = roiRegions[i].Width, h = roiRegions[i].Height }};
                        Marshal.StructureToPtr(bbox, imgInfo.ROIInfo + i * Marshal.SizeOf<TBbox>(), false);
                    }}
                }}
                
                var output = new TDetectorOutput();
                int hr = DetectorInference(_detectorHandle, ref imgInfo, ref output);
                if (hr != 0) throw new Exception("推理失败: " + hr);
                
                IntPtr resultPtr = output.pResults;
                for (int i = 0; i < output.nResultNum; i++)
                {{
                    var bbox = Marshal.PtrToStructure<TBboxScoreInfo>(resultPtr + i * Marshal.SizeOf<TBboxScoreInfo>());
                    results.Add(new DefectResult
                    {{
                        X = bbox.tBbox.x, Y = bbox.tBbox.y,
                        Width = bbox.tBbox.w, Height = bbox.tBbox.h,
                        Score = bbox.fScore, ClassId = bbox.nClassesIdx,
                        ClassName = System.Text.Encoding.UTF8.GetString(bbox.achClassesName).TrimEnd('\\0')
                    }});
                }}
                
                if (imgInfo.ROIInfo != IntPtr.Zero) Marshal.FreeHGlobal(imgInfo.ROIInfo);
                return results;
            }}
            catch (Exception ex)
            {{
                Console.WriteLine("检测失败: " + ex.Message);
                return results;
            }}
        }}
        
        /// <summary>释放资源</summary>
        public void Dispose()
        {{
            if (_detectorHandle != IntPtr.Zero) {{ DestroyDetectorHandle(_detectorHandle); _detectorHandle = IntPtr.Zero; }}
            if (_gpuBuffer != IntPtr.Zero) {{ freeImgBufferOnCUDA(_gpuBuffer); _gpuBuffer = IntPtr.Zero; }}
            Console.WriteLine("资源已释放");
        }}
        
        private TImageInfo PrepareImageInfo(Mat mat, IntPtr gpuBuffer, int maxBufferSize)
        {{
            int size = mat.Width * mat.Height * mat.Channels();
            IntPtr cpuBuffer = Marshal.AllocHGlobal(size);
            Marshal.Copy(mat.Data, 0, cpuBuffer, size);
            copyImgBufferFromCpuToGpu(cpuBuffer, maxBufferSize, mat.Width, mat.Height, 
                mat.Channels(), mat.Width * mat.Channels(), ref gpuBuffer);
            Marshal.FreeHGlobal(cpuBuffer);
            
            return new TImageInfo
            {{
                nStructSize = Marshal.SizeOf<TImageInfo>(),
                emFormat = EImageFmt.AI_BGR_U8C3,
                emAddrType = EDataAddrType.AI_DATA_ADDR_GPU,
                nChannel = mat.Channels(), nHeight = mat.Height,
                nWidth = mat.Width, nStride = mat.Width * mat.Channels(),
                nROINum = 0, ROIInfo = IntPtr.Zero, pbyBuffer = gpuBuffer
            }};
        }}
    }}
    
    public struct TImageInfo
    {{
        public int nStructSize; public EImageFmt emFormat; public EDataAddrType emAddrType;
        public int nChannel; public int nHeight; public int nStride; public int nWidth;
        public int nFrame; public int nROINum; public IntPtr ROIInfo; public IntPtr pbyBuffer;
    }}
    
    public struct TBbox {{ public float x, y, w, h; }}
    public struct TDetectorOutput {{ public IntPtr pResults; public int nResultNum; }}
    
    public struct TBboxScoreInfo
    {{
        public TBbox tBbox; public float fScore; public int nClassesIdx;
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32)]
        public byte[] achClassesName;
    }}
    
    public class DefectResult
    {{
        public float X, Y, Width, Height; public float Score; public int ClassId; public string ClassName;
    }}
    
    public enum EImageFmt {{ AI_BGR_U8C3, AI_GRAY_U8C1 }}
    public enum EDataAddrType {{ AI_DATA_ADDR_CPU, AI_DATA_ADDR_GPU }}
}}
'''


@tool
def intevega_code_generation(
    algorithm_type: str,
    detection_task: str,
    image_size: str = "8192x8192",
    roi_enabled: bool = True,
    async_inference: bool = True
) -> str:
    """
    生成 InteVega AI SDK 推理代码模板。
    
    Args:
        algorithm_type: 算法类型，可选值：
            - detector: 目标检测 (气泡、划伤、异物等)
            - segmentator: 语义分割 (缺陷区域分割)
            - classifier: 图像分类 (OK/NG分类)
            - locator: 关键点定位 (对位、测量)
            - instancesegmentator: 实例分割
        detection_task: 检测任务描述，如"显示器面板气泡检测"
        image_size: 输入图像分辨率，如"8192x8192"
        roi_enabled: 是否启用ROI区域屏蔽
        async_inference: 是否启用异步推理加速
    
    Returns:
        生成的C#代码模板和部署指南
    """
    # 算法类型映射
    algorithm_map = {
        "detector": ("目标检测", "缺陷检测、目标定位、计数统计等场景"),
        "segmentator": ("语义分割", "缺陷区域分割、像素级抠图等场景"),
        "classifier": ("图像分类", "OK/NG分类、产品分拣等场景"),
        "locator": ("关键点定位", "对位、测量、坐标提取等场景"),
        "instancesegmentator": ("实例分割", "多目标分割、个体计数等场景")
    }
    
    if algorithm_type not in algorithm_map:
        return json.dumps({
            "status": "error",
            "message": f"不支持的算法类型: {algorithm_type}",
            "supported_types": list(algorithm_map.keys())
        }, ensure_ascii=False)
    
    algorithm_name, use_case = algorithm_map[algorithm_type]
    class_name = f"{algorithm_type.capitalize()}Engine"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 格式化代码模板
    code = CSHARP_CODE_TEMPLATE.format(
        algorithm_type=algorithm_type,
        timestamp=timestamp,
        algorithm_name=algorithm_name,
        use_case=use_case,
        class_name=class_name
    )
    
    deploy_guide = '''## InteVega AI SDK 部署指南

### 环境要求
- **操作系统**: Windows 10/11 或 Linux (Docker)
- **GPU**: NVIDIA GPU with CUDA 11.x+
- **内存**: 16GB+

### 部署步骤

#### 1. 拉取仓库
```bash
git clone --recurse-submodule <repository_url>
cd intellvega-aideploy
```

#### 2. 编译 SDK
```bash
mkdir build && cd build
cmake .. && make -j$(nproc)
```

#### 3. 配置模型
将训练好的模型文件放入 `models/` 目录

#### 4. 运行测试
```bash
cd bin
./AITest --config config.json --input test.jpg
```
'''
    
    result = {
        "status": "success",
        "algorithm_type": algorithm_type,
        "algorithm_name": algorithm_name,
        "use_case": use_case,
        "image_size": image_size,
        "roi_enabled": roi_enabled,
        "async_inference": async_inference,
        "code": code.strip(),
        "deploy_guide": deploy_guide.strip(),
        "notes": [
            "代码模板基于C#，使用OpenCVSharp进行图像处理",
            "需要先部署InteVega SDK并编译对应算法的DLL",
            "ROI功能可减少无效区域的推理计算",
            "异步推理可显著提升大图处理速度"
        ]
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def intevega_model_selection(
    product_type: str,
    defect_types: list,
    precision_requirement: str,
    throughput: str
) -> str:
    """
    根据检测任务推荐 InteVega SDK 算法方案。
    
    Args:
        product_type: 产品类型，如"显示器面板"、"PCB板"、"药瓶"等
        defect_types: 缺陷类型列表，如["气泡", "划伤", "异物"]
        precision_requirement: 精度要求，如"0.1mm"
        throughput: 产能要求，如"1000件/小时"
    
    Returns:
        算法选型建议和配置参数
    """
    # 基础配置
    config = {
        "primary_algorithm": "detector",
        "secondary_algorithms": [],
        "slice_params": {
            "fSliceOverLoopRate": 0.1,
            "iSliceWidth": 2048,
            "iSliceHeight": 2048,
            "fSliceAbandonedRate": 0.05,
            "fOverLoopMergeRate": 0.3,
            "fMinDistTheta": 10.0,
            "fMinWidthThresh": 5,
            "fMinHeightThresh": 5
        }
    }
    
    # 根据产品类型调整配置
    large_area_products = ["显示器面板", "光伏板", "玻璃", "PCB板", "布料"]
    small_products = ["药瓶", "芯片", "电子元件", "五金件"]
    
    if any(p in product_type for p in large_area_products):
        config["slice_params"]["iSliceWidth"] = 4096
        config["slice_params"]["iSliceHeight"] = 4096
        config["slice_params"]["fSliceOverLoopRate"] = 0.15
        config["optimization"] = "大图推理加速模式"
    elif any(p in product_type for p in small_products):
        config["slice_params"]["iSliceWidth"] = 1024
        config["slice_params"]["iSliceHeight"] = 1024
        config["optimization"] = "标准推理模式"
    else:
        config["optimization"] = "标准推理模式"
    
    # 根据缺陷类型添加辅助算法
    if "分类" in str(defect_types) or "分拣" in str(defect_types):
        config["secondary_algorithms"].append("classifier")
    
    if "分割" in str(defect_types) or "区域" in str(defect_types):
        config["secondary_algorithms"].append("segmentator")
    
    # 生成推荐报告
    report = {
        "status": "success",
        "task_analysis": {
            "product_type": product_type,
            "defect_types": defect_types,
            "precision": precision_requirement,
            "throughput": throughput
        },
        "algorithm_recommendation": {
            "primary": config["primary_algorithm"],
            "auxiliary": config["secondary_algorithms"],
            "reason": f"根据{product_type}的{defect_types}检测需求，推荐使用{config['primary_algorithm']}作为主算法"
        },
        "inference_config": {
            "mode": config.get("optimization", "标准推理模式"),
            "parameters": config["slice_params"],
            "notes": [
                f"裁剪尺寸: {config['slice_params']['iSliceWidth']}x{config['slice_params']['iSliceHeight']}",
                f"重叠率: {config['slice_params']['fSliceOverLoopRate']*100}%",
                f"边缘丢弃率: {config['slice_params']['fSliceAbandonedRate']*100}%"
            ]
        },
        "deployment_recommendation": {
            "gpu_memory": "建议16GB+显存",
            "thread_count": "建议4-8线程",
            "batch_size": "建议2-4"
        }
    }
    
    return json.dumps(report, ensure_ascii=False, indent=2)
