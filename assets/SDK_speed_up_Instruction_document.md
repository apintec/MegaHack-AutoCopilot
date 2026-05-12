# Intevega SDK 大图加速推理使用说明文档
[TOC]

## 0 概述
&emsp;&emsp; 本文档目的在于向读者介绍如何在C#端调用优化后的SDK推理库的方法，包括检测算法的使用，分割算法的使用，稠密点定位算法的使用，多模型串联的使用（以检测+分类多模型使用为例）。


## 1 C# 公共结构体的定义
### 1.1 单图像输入结构体变更
&emsp;&emsp; C++ SDK内部对公共输入数据的结构体增加了ROI信息的参数，支持ROI数据的传入，因此在C#端需要进行对应的更新，以便于C#端调用C++ SDK的接口。
&emsp;&emsp; 如下所示，左边时原始C#单图输入图像数据结构体的定义，右图是在C#端增加了ROI信息的结构体定义。`nROINum` 是 `int` 类型数据，表示传入的 ROI 的数量， `ROIInfo` 是 `IntPtr` 类型数据，指向 ROI 信息的指针（TBbox: x,y,w,h）。

```
[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 8)]
public struct TImageInfo            public struct TImageInfo
{                                   {
    public int nStructSize;             public int nStructSize;
    public EImageFmt emFormat;          public EImageFmt emFormat;    // 图像格式
    public EDataAddrType emAddrType;    public EDataAddrType emAddrType;  // 图像缓存地址类型
    public int nChannel;                public int nChannel;
    public int nHeight;                 public int nHeight;
    public int nStride;                 public int nStride;    // 每行字节数(d3d显示=pitch, ffmpeg解码=linesize, ffmpeg转码=stride)
    public int nWidth;                  public int nWidth;
    public int nFrame;                  public int nFrame;
                             ------->   public int nROINum;
                             ------->   public IntPtr ROIInfo;      // 调用者 申请，由 调用者 释放
    public IntPtr pbyBuffer;            public IntPtr pbyBuffer;    // 缓存由 调用者 申请，由 调用者 释放
};                                  };
```

### 1.2 大图裁剪推理参数说明
```C#
    public struct TModelOpenParam
    {
        public float fSliceOverLoopRate;    // 大图裁剪的重叠率
        public int iSliceWidth;             // 大图裁剪的宽度
        public int iSliceHeight;            // 大图裁剪的高度
        public float fSliceAbandonedRate;   // 大图裁剪的边缘丢弃率

        public float fOverLoopMergeRate;    // 小图结果合并的 iou 阈值
        public float fMinDistTheta;         // 小图结果合并的距离阈值

        public float fMinWidthThresh;       // 检测框最小宽度阈值，小于该值的被过滤
        public float fMinHeightThresh;      // 检测框最小高度阈值，小于该值的被过滤
    }
```

## 2 GPU 显存的申请与释放、图像数据的拷贝
&emsp;&emsp; 避免对GPU显存的频繁申请与释放，建议在程序初始化时，预先申请足够大的GPU显存复用，在程序结束时，释放GPU显存。

&emsp;&emsp; 图像数据的拷贝，建议使用CUDA的API，具体使用方法如下所示：
``` C#
// 1、申请GPU显存
IntPtr gpuBufferAdd;
gpuBufferAdd = Marshal.AllocHGlobal(4);
int maxBufSize = 500 * 500 * 3;
mallocImgBufferOnCUDA(ref gpuBufferAdd, maxBufSize);

// 2、拷贝图像数据到GPU显存
ConvertMatToTImageInfo(imagePath, out TImageInfo imgInfo, EDataAddrType.AI_DATA_ADDR_GPU, ref gpuBufAdd, maxBufSize)
{
    Mat srcMat = Cv2.ImRead(imgPath);

    IntPtr cpuBuffer;
    int channels = srcMat.Channels();
    int stride = srcMat.Width * channels;

    int size = stride * srcMat.Height;
    cpuBuffer = Marshal.AllocHGlobal(size);

    Byte[] bytes = new Byte[size];
    Marshal.Copy(srcMat.DataStart, bytes, 0, size);
    Marshal.Copy(bytes, 0, cpuBuffer, size);

    EImageFmt dstEmFormat;

    if (channels == 3)
    {
        dstEmFormat = Interface.EImageFmt.AI_BGR_U8C3;
    }
    else if (channels == 1)
    {
        dstEmFormat = Interface.EImageFmt.AI_GRAY_U8C1;
    }
    else
    {
        throw new Exception("unsupport img format!");
    }

    IntPtr bboxPtr = IntPtr.Zero;
    if (bboxArray != null)
    {
        // 分配非托管内存并拷贝数据
        bboxPtr = Marshal.AllocHGlobal(Marshal.SizeOf<TBbox>() * bboxArray.Length);
        for (int i = 0; i < bboxArray.Length; i++)
        {
            Marshal.StructureToPtr(bboxArray[i], bboxPtr + i * Marshal.SizeOf<TBbox>(), false);
        }
    }

    dst = new Interface.TImageInfo
    {
        emFormat = dstEmFormat,
        nWidth = srcMat.Width,
        nHeight = srcMat.Height,
        nStride = stride,
        nChannel = channels,
        nROINum = 0,
        ROIInfo = IntPtr.Zero,
    };

    if (bboxPtr != IntPtr.Zero)
    {
        dst.nROINum = bboxArray.Length;
        dst.ROIInfo = bboxPtr;
    }

    if (dataAddrType == EDataAddrType.AI_DATA_ADDR_GPU)
    {
        int hrCode = copyImgBufferFromCpuToGpu(cpuBuffer, maxBufSize, srcMat.Width, srcMat.Height, channels, stride, ref gpuBufAdd);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(Detection.getAIErrorMessage()));
        dst.emAddrType = Interface.EDataAddrType.AI_DATA_ADDR_GPU;
        dst.pbyBuffer = gpuBufAdd;

        // 释放 cpu 数据图像
        Marshal.FreeHGlobal(cpuBuffer);
        cpuBuffer = IntPtr.Zero;
    }
    else
    {
        dst.emAddrType = Interface.EDataAddrType.AI_DATA_ADDR_CPU;
        dst.pbyBuffer = cpuBuffer;
    }
}

// 3、释放GPU显存
freeImgBufferOnCUDA(gpuBufferAdd);
```

## 3 目标检测使用示例
&emsp;&emsp; 本次更新了检测输出结构体的定义，使用指针的方式传输检测的结果，与之前的list方式相比，使用指针的方式传输检测的结果，避免了对数量的限制，适用于大图上多数量目标的情况。如下所示，`TBatchDetectorOutInfoPtr` 还是和原来一样，最大的检测数量为8个，适用List管理，`TSingleDetectorInfoPtr` 中 `atObjectInfo` 更新为 `IntPtr`类型, 保存检测的结果。
```
// ptr output
[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 1)]
public struct TBboxScoreInfo
{
    public TBbox tBbox;
    public int nClassesIdx;
    [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32)]
    public byte[] achClassesName; // 类别的名字，char[] 改成 byte[] ，支持中文
    public float fConfidence;
};

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 1)]
public struct TSingleDetectorInfoPtr
{
    public int nStructSize;
    public int nNumObject;
    public IntPtr atObjectInfo;  <----- 指针，指向检测结果的结构体，TBboxScoreInfo
};


[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 1)]
public struct TBatchDetectorOutInfoPtr
{
    public int nStructSize;
    public int nNumOut;
    [MarshalAs(UnmanagedType.ByValArray, ArraySubType = UnmanagedType.LPStruct, SizeConst = 8)]
    public Interface.TSingleDetectorInfoPtr[] atDetectorInfo;
};
```

&emsp;&emsp; 检测模块大图裁推理的使用流程大致如下所示
``` C#
main()
{
    // 1、预先申请GPU内存
    IntPtr gpuBufferAdd;
    gpuBufferAdd = Marshal.AllocHGlobal(4);
    int maxBufSize = 500 * 500 * 3;     // 根据实际输入最大的 width、height、channel 来设置
    mallocImgBufferOnCUDA(ref gpuBufferAdd, maxBufSize);

    // 2、创建模型推理句柄
    string strConfigPath = "hslp.json";
    var InitResults = GetAvailableBigImageDetectionHandler(strConfigPath); 
    {
        // 1、创建推理日志
        int hrCode = setupDetectorLogLevel(1);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 2、获取模型版本信息
        char[] version = new char[32];
        hrCode = getDetectorVersion(version);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 3、解析配置文件
        ModelParams.TModelOpenParam TOpenParam = new ModelParams.TModelOpenParam();
        TOpenParam.nStructSize = Marshal.SizeOf(TOpenParam);

        IntPtr ptrJsonPath = Marshal.StringToHGlobalAnsi(configPath);
        hrCode = parseJsonToOpenParam(ptrJsonPath, ref TOpenParam);
        Marshal.FreeHGlobal(ptrJsonPath);
        ptrJsonPath = IntPtr.Zero;
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 4、更新裁剪推理参数
        TOpenParam.iSliceWidth = 1280;// 119;//  2560;
        TOpenParam.iSliceHeight = 1280;//120;// srcMat.Rows;
        TOpenParam.fSliceOverLoopRate = 0.4f;
        TOpenParam.fOverLoopMergeRate = 0.15f;
        TOpenParam.tThreshSet.fConfThresh = 0.25f;

        // 5、创建模型推理句柄
        IntPtr InferHandle = Marshal.AllocHGlobal(0);
        hrCode = createDetectorHandle(ref TOpenParam, InferHandle);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        return new Tuple<IntPtr, ModelParams.TModelOpenParam>(InferHandle, TOpenParam);
    }
    //包括 日志初始化，获取模型版本信息，解析配置文件，创建模型推理句柄

    // 3、定义输入输出数据
    //定义输入图像信息
    Interface.TBatchImageInfo tInputInfo = new Interface.TBatchImageInfo()
    {
        atImageInfo = new Interface.TImageInfo[8],
    };
    tInputInfo.nNumImg = 1;
    tInputInfo.nStructSize = Marshal.SizeOf(tInputInfo);

    //定义输出信息（推理结果）
    TBatchDetectorOutInfoPtr detectorOutInfo = new TBatchDetectorOutInfoPtr();
    detectorOutInfo.nStructSize = Marshal.SizeOf(detectorOutInfo);

    // 4、图像数据拷贝 cpu->gpu
    ConvertMatToTImageInfo(imagePath, out TImageInfo imgInfo, EDataAddrType.AI_DATA_ADDR_GPU, ref gpuBufAdd, maxBufSize); 
    for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
    {
        tInputInfo.atImageInfo[idxBatch] = imgInfo;
    }

    // 5、模型推理, 推理接口和之前一致，加了后缀Ptr，表示使用指针的方式传输检测的结果
    int hrCode = inferDetectorAnalysisPtr(InferHandle, ref tInputInfo, ref detectorOutInfo);

    // 6、解析检测结果
    for (int i = 0; i < detectorOutInfo.nNumOut; ++i)
    {
        TSingleDetectorInfoPtr detectorInfo = detectorOutInfo.atDetectorInfo[i];
        Console.WriteLine($"Infer batch {i} has {detectorInfo.nNumObject} objects.");

        // 解析 atObjectInfo 指针
        TBboxScoreInfo[] objectInfos = new TBboxScoreInfo[detectorInfo.nNumObject];
        Console.WriteLine(detectorInfo.nNumObject);
        for (int j = 0; j < detectorInfo.nNumObject; j++)
        {
            IntPtr ptr = new IntPtr(detectorInfo.atObjectInfo.ToInt64() + j * Marshal.SizeOf(typeof(TBboxScoreInfo)));
            objectInfos[j] = Marshal.PtrToStructure<TBboxScoreInfo>(ptr);
        }
        
        // 处理 objectInfos 数组
        for (int idx = 0; idx < objectInfos.Length; ++idx)
        {
            var objInfo = objectInfos[idx];
            Rect rect = new Rect(objInfo.tBbox.nLeftTopX,
                                 objInfo.tBbox.nLeftTopY,
                                 objInfo.tBbox.nWidth,
                                 objInfo.tBbox.nHeight);
            Cv2.Rectangle(srcMat, rect, scalarList[objInfo.nClassesIdx], 2);
            Console.WriteLine("[  Bbox: {0}, {1}, {2}, {3}; ClassIndx: {4}; Confidence: {5}]",
                                objInfo.tBbox.nLeftTopX,
                                objInfo.tBbox.nLeftTopY,
                                objInfo.tBbox.nWidth,
                                objInfo.tBbox.nHeight,
                                objInfo.nClassesIdx,
                                objInfo.fConfidence);
        }
    }

    // 7、使用指针输出结构体，需要调用释放接口释放指针
    releaseDetectorInfoPtr(ref detectorOutInfo);

    // 8、推理结束释放图像/ROI 信息资源
    CommonFunc.ReleaseInputBuffer(tInputInfo)
    {
        for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
            {
                if (tInputInfo.atImageInfo[idxBatch].emAddrType == EDataAddrType.AI_DATA_ADDR_CPU)
                {
                    Marshal.FreeHGlobal(tInputInfo.atImageInfo[idxBatch].pbyBuffer);
                    tInputInfo.atImageInfo[idxBatch].pbyBuffer = IntPtr.Zero;
                }

                if (tInputInfo.atImageInfo[idxBatch].ROIInfo != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(tInputInfo.atImageInfo[idxBatch].ROIInfo);
                    tInputInfo.atImageInfo[idxBatch].ROIInfo = IntPtr.Zero;
                }
            }
    }

    // 9、释放推理句柄
    DestroyDetectionHandler(InitResults.Item1);

    // 10、释放GPU显存
    freeImgBufferOnCUDA(gpuBufferAdd);
}
```



## 3 语义分割使用示例
&emsp;&emsp; 语义分割原本就是使用的buffer在 C# 和 C++ 交互，因此在推理接口没有变动，下面介绍语义分割大图裁剪推理GPU加速推理的使用方法。

&emsp;&emsp; <span style="color:red;">语义分割后处理使用了GPU加速，因此在创建推理前，需要先设置裁剪的参数信息，SDK内部根据裁剪的 W、H 信息申请 GPU 上的 buffer 预处理，这点很重要，不然会导致大图推理结果的错误。（如下面 2、创建模型推理句柄 中第4点所示）</span>
```C#
    // 1、预先申请GPU内存
    IntPtr gpuBufferAdd;
    gpuBufferAdd = Marshal.AllocHGlobal(4);
    int maxBufSize = 500 * 500 * 3;     // 根据实际输入最大的 width、height、channel 来设置
    mallocImgBufferOnCUDA(ref gpuBufferAdd, maxBufSize);

    // 2、创建模型推理句柄
    string strConfigPath = "hslp.json";
    var InitResults = GetAvailableBigImageSegmentationHandler(strConfigPath);
    {
        // 1、创建分割推理日志
        int hrCode = setupSegmentationLogLevel(1);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 2、获取模型版本信息
        char[] version = new char[32];
        hrCode = getSemanticSegVersion(version);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 3、解析配置文件
        ModelParams.TModelOpenParam TOpenParam = new ModelParams.TModelOpenParam();
        TOpenParam.nStructSize = Marshal.SizeOf(TOpenParam);

        IntPtr ptrJsonPath = Marshal.StringToHGlobalAnsi(configPath);
        hrCode = parseJsonToOpenParam(ptrJsonPath, ref TOpenParam);
        Marshal.FreeHGlobal(ptrJsonPath);
        ptrJsonPath = IntPtr.Zero;
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));
        
        // 4、更新裁剪推理参数 <更新裁剪相关参数>
        TOpenParam.iSliceHeight = 160;
        TOpenParam.iSliceWidth = 304;
        TOpenParam.fSliceOverLoopRate = 0.2f;
        TOpenParam.fSliceAbandonedRate = 0.25f;

        // 5、创建模型推理句柄
        IntPtr InferHandle = Marshal.AllocHGlobal(0);
        hrCode = createSemanticSegHandle(ref TOpenParam, InferHandle);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));
        
        return new Tuple<IntPtr, ModelParams.TModelOpenParam>(InferHandle, TOpenParam);    
    }

    // 3、定义输入输出数据
    //定义输入图像信息
    Interface.TBatchImageInfo tInputInfo = new Interface.TBatchImageInfo()
    {
        atImageInfo = new Interface.TImageInfo[8],
    };
    tInputInfo.nNumImg = 1;
    tInputInfo.nStructSize = Marshal.SizeOf(tInputInfo);

    //定义输出信息（推理结果，外部申请内存）
    TBatchSemanticSegInfo segOutInfo = new TBatchSemanticSegInfo()
    {
        atSemanticSegInfo = new TSingleSemanticSeg[8],
    };
    segOutInfo.nNumOut = tInputInfo.nNumImg;
    segOutInfo.nStructSize = Marshal.SizeOf(segOutInfo);

    // 4、图像数据拷贝 cpu->gpu
    for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
    {
        ConvertMatToTImageInfo(imagePath, out TImageInfo imgInfo, EDataAddrType.AI_DATA_ADDR_CPU, ref gpuBufAdd, maxBufSize); // cpu\gpu
        tInputInfo.atImageInfo[idxBatch] = imgInfo;     // 更新输入

        // 输出 buffer 申请
        IntPtr outBuffer = Marshal.AllocHGlobal(imgInfo.nWidth * imgInfo.nHeight);
        segOutInfo.atSemanticSegInfo[idxBatch].pbyBuffer = outBuffer;
        segOutInfo.atSemanticSegInfo[idxBatch].nHeight = imgInfo.nHeight;
        segOutInfo.atSemanticSegInfo[idxBatch].nWidth = imgInfo.nWidth;
    }

    // 5、模型推理, 推理接口和之前一致，加了后缀Ptr，表示使用指针的方式传输检测的结果
    int hrCode = inferSemanticSegAnalysis(InferHandle, ref tInputInfo, ref segOutInfo);

    // 6、解析检测结果

    // 7、释放分割推理结果buffer
    for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
    {
       Marshal.FreeHGlobal(segOutInfo.atSemanticSegInfo[idxBatch].pbyBuffer);
       segOutInfo.atSemanticSegInfo[idxBatch].pbyBuffer = IntPtr.Zero; ;
    }

    // 8、推理结束释放图像/ROI 信息资源
    CommonFunc.ReleaseInputBuffer(tInputInfo)
    {
        for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
            {
                if (tInputInfo.atImageInfo[idxBatch].emAddrType == EDataAddrType.AI_DATA_ADDR_CPU)
                {
                    Marshal.FreeHGlobal(tInputInfo.atImageInfo[idxBatch].pbyBuffer);
                    tInputInfo.atImageInfo[idxBatch].pbyBuffer = IntPtr.Zero;
                }

                if (tInputInfo.atImageInfo[idxBatch].ROIInfo != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(tInputInfo.atImageInfo[idxBatch].ROIInfo);
                    tInputInfo.atImageInfo[idxBatch].ROIInfo = IntPtr.Zero;
                }
            }
    }

    // 9、释放推理句柄
    DestroySegmentationHandler(InitResults.Item1);

    // 10、推理结束释放GPU显存
    freeImgBufferOnCUDA(gpuBufferAdd);
```



## 3 稠密点定位使用示例
&emsp;&emsp; 稠密点定位之前最大只支持512个点的输出，本次更新和检测类似，使用指针接收推理的结果，下面介绍稠密点定位模块大图裁剪推理GPU加速推理的使用方法。
&emsp;&emsp; 稠密点定位输出结果体的定义如下：
```
// ptr output
[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 1)]
public struct TCoorScoreInfo
{
    public TCoor tCoor;
    public float fConfidence;
};

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 1)]
public struct TSingleLocationInfoPtr
{
    public int nStructSize;
    public int nNumPoint;
    public IntPtr atCoorScoreInfo;      <----- 指针，指向检测结果的结构体，TCoorScoreInfo
};

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi, Pack = 1)]
public struct TBatchLocationInfoPtr
{
    public int nStructSize;
    public int nNumOut;
    [MarshalAs(UnmanagedType.ByValArray, ArraySubType = UnmanagedType.LPStruct, SizeConst = 8)]
    public TSingleLocationInfoPtr[] atLocationInfo;
};


```
&emsp;&emsp; 稠密点定位的使用方法和之前的检测和分割类似，下面是稠密点定位的使用示例：
```C#
    // 1、预先申请GPU内存
    IntPtr gpuBufferAdd;
    gpuBufferAdd = Marshal.AllocHGlobal(4);
    int maxBufSize = 500 * 500 * 3;     // 根据实际输入最大的 width、height、channel 来设置
    mallocImgBufferOnCUDA(ref gpuBufferAdd, maxBufSize);

    // 2、创建模型推理句柄
    string strConfigPath = "hslp.json";
    var InitResults = GetAvailableBigImageLocationHandler(strConfigPath);
    {
        // 1、创建稠密点定位模块推理日志
        int hrCode = setupLocatorLogLevel(1);

        // 2、获取模型版本信息
        char[] version = new char[32];
        hrCode = getLocatorVersion(version);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 3、解析配置文件
        ModelParams.TModelOpenParam TOpenParam = new ModelParams.TModelOpenParam();
        TOpenParam.nStructSize = Marshal.SizeOf(TOpenParam);

        IntPtr ptrJsonPath = Marshal.StringToHGlobalAnsi(configPath);
        hrCode = parseJsonToOpenParam(ptrJsonPath, ref TOpenParam);
        Marshal.FreeHGlobal(ptrJsonPath);
        ptrJsonPath = IntPtr.Zero;
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        // 4、更新裁剪推理参数
        TOpenParam.iSliceWidth = 224;
        TOpenParam.iSliceHeight = 224;
        TOpenParam.fSliceOverLoopRate = 0.0f;
        TOpenParam.fOverLoopMergeRate = 0.00f;
        TOpenParam.tThreshSet.fConfThresh = 0.25f;
        TOpenParam.fMinDistTheta = 3;  // 根据点之间的距离阈值去除重复点，该距离是点之间的绝对像素距离

        // 5、创建模型推理句柄
        IntPtr InferHandle = Marshal.AllocHGlobal(0);
        hrCode = createLocatorHandle(ref TOpenParam, InferHandle);
        if (hrCode != 0) throw new Exception(Marshal.PtrToStringAnsi(getAIErrorMessage()));

        return new Tuple<IntPtr, ModelParams.TModelOpenParam>(InferHandle, TOpenParam);
    }

    // 3、定义输入输出数据
    //定义输入图像信息
    Interface.TBatchImageInfo tInputInfo = new Interface.TBatchImageInfo()
    {
        atImageInfo = new Interface.TImageInfo[8],
    };
    tInputInfo.nNumImg = 1;
    tInputInfo.nStructSize = Marshal.SizeOf(tInputInfo);

    //定义输出信息（推理结果，外部申请内存）
    TBatchLocationInfoPtr locatorOutInfo = new TBatchLocationInfoPtr()
    {
        atLocationInfo = new TSingleLocationInfoPtr[8],
    };
    locatorOutInfo.nNumOut = tInputInfo.nNumImg;
    locatorOutInfo.nStructSize = Marshal.SizeOf(locatorOutInfo);

    // 4、图像数据拷贝 cpu->gpu
    for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
    {
        ConvertMatToTImageInfo(imagePath, out TImageInfo imgInfo, EDataAddrType.AI_DATA_ADDR_CPU, ref gpuBufAdd, maxBufSize); // cpu\gpu
        tInputInfo.atImageInfo[idxBatch] = imgInfo;     // 更新输入
    }

    // 5、模型推理, 推理接口和之前一致，加了后缀Ptr，表示使用指针的方式传输检测的结果
    int nPointIdx = 0;
    hrCode = inferLocatorAnalysisPtr(InferHandle, ref tInputInfo, nPointIdx, ref locatorOutInfo);

    // 6、解析检测结果
    for (int i = 0; i < locatorOutInfo.nNumOut; ++i)
    {
        Console.WriteLine("-------- batch = {0} --------- {1}", i, locatorOutInfo.atLocationInfo[i].nNumPoint);

        // 解析 atObjectInfo 指针
        TCoorScoreInfo[] pointsInfos = new TCoorScoreInfo[locatorOutInfo.atLocationInfo[i].nNumPoint];

        for (int j = 0; j < locatorOutInfo.atLocationInfo[i].nNumPoint; j++)
        {
            IntPtr ptr = new IntPtr(locatorOutInfo.atLocationInfo[i].atCoorScoreInfo.ToInt64() + j * Marshal.SizeOf(typeof(TCoorScoreInfo)));
            pointsInfos[j] = Marshal.PtrToStructure<TCoorScoreInfo>(ptr);
        }

        for (int j = 0; j < pointsInfos.Length; ++j)
        {
            Cv2.Circle(srcMat, new OpenCvSharp.Point(pointsInfos[j].tCoor.nX, pointsInfos[j].tCoor.nY), 1, new Scalar(0, 0, 255));
        }
    }

    // 7、释放推理结果buffer
    releaseLocatorInfoPtr(locatorOutInfo);

    // 8、推理结束释放图像/ROI 信息资源
    CommonFunc.ReleaseInputBuffer(tInputInfo)
    {
        for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
            {
                if (tInputInfo.atImageInfo[idxBatch].emAddrType == EDataAddrType.AI_DATA_ADDR_CPU)
                {
                    Marshal.FreeHGlobal(tInputInfo.atImageInfo[idxBatch].pbyBuffer);
                    tInputInfo.atImageInfo[idxBatch].pbyBuffer = IntPtr.Zero;
                }

                if (tInputInfo.atImageInfo[idxBatch].ROIInfo != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(tInputInfo.atImageInfo[idxBatch].ROIInfo);
                    tInputInfo.atImageInfo[idxBatch].ROIInfo = IntPtr.Zero;
                }
            }
    }

    // 9、释放推理句柄
    DestroyLocationHandler(InitResults.Item1);

    // 10、释放GPU显存
    freeImgBufferOnCUDA(gpuBufferAdd);
```



## 3 检测+分类多模型推理使用示例
&emsp;&emsp; 基于 GPU 图像数据缓存复用和 ROI 推理参数的引入，大大降低了多模型串联推理中 数据格式转换的时间，加快推理速度。下面给出检测+分类模型串联推理的使用实例。

```C#
main()
{
    // 1、预先申请GPU内存
    IntPtr gpuBufferAdd;
    gpuBufferAdd = Marshal.AllocHGlobal(4);
    int maxBufSize = 55000 * 2592 * 3;
    Detection.mallocImgBufferOnCUDA(ref gpuBufferAdd, maxBufSize);


    // 2、初始化检测、分类模型推理句柄
    string strConfigPathDet = "det_hslp_tvg.json";
    var InitResultsDet = Detection.GetAvailableBigImageDetectionHandler(strConfigPathDet);

    string strConfigPathCls = "cls_hslp_tvg.json";
    var InitResultsCls = Classification.GetAvailableClassificationHandler(strConfigPathCls);

    // 3、 定义输入输出图像信息
    // 定义输入图像信息
    Interface.TBatchImageInfo tInputInfo = new Interface.TBatchImageInfo()
    {
        atImageInfo = new Interface.TImageInfo[8],
    };
    tInputInfo.nNumImg = 1;
    tInputInfo.nStructSize = Marshal.SizeOf(tInputInfo);

    //定义检测输出信息（推理结果）
    TBatchDetectorOutInfoPtr detectorOutInfo = new TBatchDetectorOutInfoPtr();
    detectorOutInfo.nStructSize = Marshal.SizeOf(detectorOutInfo);

    //定义分类输出信息（推理结果）
    TBatchClassifierInfoPtr classifierOutInfo = new TBatchClassifierInfoPtr();
    classifierOutInfo.nStructSize = Marshal.SizeOf(classifierOutInfo);


    // 3、 检测模型推理输入数据处理
    ConvertMatToTImageInfo(strImgPath, out TImageInfo imgInfo, EDataAddrType.AI_DATA_ADDR_GPU, ref gpuBufferAdd, maxBufSize);
    for (int idxBatch = 0; idxBatch < tInputInfo.nNumImg; idxBatch++)
    {
        tInputInfo.atImageInfo[idxBatch] = imgInfo;
    }

    // 4、检测模型推理
    Detection.inferDetectorAnalysisPtr(InitResultsDet.Item1, ref tInputInfo, ref detectorOutInfo);

    // 5、检测推理结果解析，将检测结果的 ROI 信息提取出来，用于后续分类模型推理
    var ParserInferRes = parser_Detect_result(detectorOutInfo);
    {
        List<ROI> inferCandiRes = new List<ROI>();

        for (int i = 0; i < detectOutInfo.nNumOut; ++i)
        {
            TSingleDetectorInfoPtr detectorInfo = detectOutInfo.atDetectorInfo[i];
            //Console.WriteLine($"Infer batch {i} has {detectorInfo.nNumObject} objects.");

            // 解析 atObjectInfo 指针
            TBboxScoreInfo[] objectInfos = new TBboxScoreInfo[detectorInfo.nNumObject];
            for (int j = 0; j < detectorInfo.nNumObject; j++)
            {
                IntPtr ptr = new IntPtr(detectorInfo.atObjectInfo.ToInt64() + j * Marshal.SizeOf(typeof(TBboxScoreInfo)));
                objectInfos[j] = Marshal.PtrToStructure<TBboxScoreInfo>(ptr);
            }

            // 处理 objectInfos 数组
            for (int idx = 0; idx < objectInfos.Length; ++idx)
            {
                var objInfo = objectInfos[idx];
                inferCandiRes.Add(new ROI(objInfo.tBbox.nLeftTopX,
                                            objInfo.tBbox.nLeftTopY,
                                            objInfo.tBbox.nLeftTopX + objInfo.tBbox.nWidth,
                                            objInfo.tBbox.nLeftTopY + objInfo.tBbox.nHeight,
                                            objInfo.fConfidence,
                                            objInfo.nClassesIdx));
            }
        }
        return new List<ROI>(inferCandiRes);
    }

    // 6、使用指针输出结构体，需要调用释放接口释放指针
    releaseDetectorInfoPtr(ref detectorOutInfo);

    // 7、 分类模型推理
    var InferResultsCls = Classification.ClassifyCls(InitResultsCls.Item1, InitResultsCls.Item2, tInputInfo, classifierOutInfo, ParserInferRes);
    {

        int remaintilenums = ParserInferRes.Count;
        TBbox[] bboxArray = new TBbox[remaintilenums];
        for (var idx_tile= 0; idx_tile < remaintilenums; idx_tile++)
        {
            bboxArray[idx_tile].nLeftTopX = (int)ParserInferRes[idx_tile].X1;
            bboxArray[idx_tile].nLeftTopY = (int)ParserInferRes[idx_tile].Y1;
            bboxArray[idx_tile].nWidth = (int)ParserInferRes[idx_tile].X2 - (int)ParserInferRes[idx_tile].X1;
            bboxArray[idx_tile].nHeight = (int)ParserInferRes[idx_tile].Y2 - (int)ParserInferRes[idx_tile].Y1;
        }

        if (tInputInfo.atImageInfo[0].ROIInfo != IntPtr.Zero)
        {
            Marshal.FreeHGlobal(tInputInfo.atImageInfo[0].ROIInfo);
            tInputInfo.atImageInfo[0].ROIInfo = IntPtr.Zero;
        }

        // 分配非托管内存并拷贝数据
        IntPtr bboxPtr = Marshal.AllocHGlobal(Marshal.SizeOf<TBbox>() * bboxArray.Length);
        for (int i = 0; i < bboxArray.Length; i++)
        {
            Marshal.StructureToPtr(bboxArray[i], bboxPtr + i * Marshal.SizeOf<TBbox>(), false);
        }

        tInputInfo.atImageInfo[0].nROINum = bboxArray.Length;
        tInputInfo.atImageInfo[0].ROIInfo = bboxPtr;

        int hrCode = inferClassifierAnalysisPtr(InferHandle, ref tInputInfo, ref classifierOutInfo);
        if (hrCode != 0) throw new Exception("Failed to infer Data in cls task.");
        return classifierOutInfo;
    }

    // 8、 分类模型推理结果解析&后处理
    for (int idx_batch = 0; idx_batch < InferResultsCls.nNumOut; idx_batch++)
    {
       TSingleClassifierInfoPtr clssifySingleInfo = InferResultsCls.atClssifierOutInfo[idx_batch];
       //Console.WriteLine($"Infer batch {i} has {detectorInfo.nNumObject} objects.");

       // 解析 atObjectInfo 指针
       TClsInfo[] clsInfos = new TClsInfo[clssifySingleInfo.nNumOut];
       for (int j = 0; j < clssifySingleInfo.nNumOut; j++)
       {
           IntPtr ptr = new IntPtr(clssifySingleInfo.atObjectInfo.ToInt64() + j * Marshal.SizeOf(typeof(TClsInfo)));
           clsInfos[j] = Marshal.PtrToStructure<TClsInfo>(ptr);
       }

       // 处理 objectInfos 数组
       for (int idx = 0; idx < clsInfos.Length; ++idx)
       {
           var objInfo = clsInfos[idx];
           Console.WriteLine("Num.{0}: classIdx={1}, conf={2} \r", idx, objInfo.nClassesIdx, objInfo.fConfidence)；
       }
    }

    // 9、释放分类模型推理结果指针数据
    releaseClassifyInfoPtr(InferResultsCls);

    // 10、推理结束释放图像/ROI 信息内存
    ReleaseInputBuffer(tInputInfo);

    // 11、释放模型推理句柄
    DestroyDetectionHandler(InitResultsDet.Item1);
    DestroyClassificationHandler(InitResultsCls.Item1);

    // 12、释放 GPU 显存
    freeImgBufferOnCUDA(gpuBufferAdd);
}   
```