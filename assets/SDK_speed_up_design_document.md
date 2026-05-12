# Intevega SDK 大图推理加速优化设计文档
[TOC]

1. 目的
    1. 对超大分辨率图像大图进行推理加速优化，降低大图推理耗时。
    2. 支持多模型使用优化。（以检测+分类模型为例）
2. 方案
    1. 支持输入ROI区域屏蔽干扰区域；
    2. 异步推理方案，支持预处理、后处理、推理三个阶段异步执行；
    3. 预处理、后处理CUDA加速；
    4. 大图数据在GPU上缓存共享；
    5. 以检测+分类多模型使用为例，支持多模型使用的优化
3. 优化模块
   1. 大图数据在GPU上缓存共享；
   2. 线程池管理多线程异步并行执行；
   3. 非ROI区域推理屏蔽；
   4. 目标检测
   5. 语义分割
   6. 稠密点定位
   7. 分类


## 0 概述
&emsp;&emsp; 考虑不同算法后处理的复杂程度，依据实际测试结论，针对上述算法采用不同的推理方案，具体来说，对检测模型采用异步推理方案，对分类、语义分割、稠密点定位模型采用同步推理方案。两种方案的pipeline如下所示：
<center><img src="./images/大图加速多线程异步推理.jpg" style="width:75%"></center>
<center>图1. 图加速多线程异步推理pipeline</center>


<center><img src="./images/大图推理单线程加速.jpg" style="width:75%"></center>
<center>图2. 图加速多线程异步推理pipeline</center>

## 1 大图数据在GPU上缓存共享
&emsp;&emsp; 预先在GPU上申请一块足够大的缓存空间，将大图数据缓存到GPU上，避免每次推理都需要从CPU拷贝到GPU；同时能够支持不同模型之间的共享，避免重复申请缓存空间。因为不同算法模块间预处理方式不同，此处缓存的图像时最原始的图像数据，后续的预处理在各算法模块中的预处理阶段单独执行。

&emsp;&emsp;此功能主要开发三个接口，实现主要在 `lib_common.dll` 中，具体实现代码路径如下：**`intellvega-aideploy_common/include/preprocess.h`**
```
// 申请GPU缓存空间 iMaxBufferSize = width * height * channels * sizeof(unsigned char)
MegaAIResult mallocImgBufferOnCUDA(IN void** gpuImgBuffer, IN const int iMaxBufferSize);


// 拷贝数据到GPU缓存空间，会首先判断当前传入的图像大小和当前GPU缓存空间支持的最大容量，若传入的图像大小大于当前GPU缓存空间大小，则释放当前GPU缓存空间，重新申请空间
copyImgBufferFromCpuToGpu(IN const void* cpuImgBuffer, IN const int iMaxBufferSize, IN const int width, IN const int height, IN const int channels, IN const int stride, OUT void** gpuImgBuffer);

// 释放GPU缓存空间
MegaAIResult freeImgBufferOnCUDA(IN void* gpuImgBuffer);
``` 



## 1 线程池管理异步线程
&emsp;&emsp; 线程池管理异步线程，主要是为了实现异步推理，具体来说，线程池管理异步线程的pipeline如下所示：
<center><img src="./images/threadpool.png" style="width:75%"></center>
<center>图3. 线程池</center>

### 1.1 为什么要用线程池
- 降低资源消耗。通过重复利用已创建的线程降低线程创建、销毁线程造成的消耗。
- 提高响应速度。当任务到达时，任务可以不需要等到线程创建就能立即执行。
- 提高线程的可管理性。线程是稀缺资源，如果无限制的创建，不仅会消耗系统资源，还会降低系统的稳定性，使用线程池可以进行统一的分配、调优和监控

### 1.2 threadpool 线程池类参数详解
|    参数    |    说明    |
|------------|------------|
| vector<thread> _pool;         | 线程池 |
| queue<Task> _tasks;           | 任务队列 |
| mutex _lock;                  | 任务队列同步锁 |
| condition_variable _task_cv;  | 多线程条件变量 |
| atomic<bool> _run{ true };    | 线程池是否执行 |
| atomic<int>  _idlThrNum{ 0 }; | 空闲线程数量 |


### 1.3 线程池类实现
&emsp;&emsp; 线程池类的实现在lib_common.dll下，具体实现代码路径如下：**`intellvega-aideploy_common/include/threadPool.h`**



## 2 ROI区域预处理
&emsp;&emsp; 加速大图推理速度的其中一条策略是对非ROI区域进行屏蔽，以减少不必要的计算，输入图像的尺寸减少，推理效率也会相应的提升。因此在定义的公共输入接口新增了ROI区域信息。

### 2.1 tagImageInfo 结构体更新说明
&emsp;&emsp; 如下所示：左右分别是新老接口的对比，差别主要在 `tagImageInfo` 结构体中新增了nROINum和ROIInfo两个字段，nROINun记录传入ROI的数量，ROIInfo是一个TBbox类型的指针，避免了和C#交互时数量限制，<span style="color:red;">由调用者申请，由调用者释放</span>。
```C++
// old                          new
typedef struct tagImageInfo     typedef struct tagImageInfo                        
{                               {
int nStructSize;                    int nStructSize;
EImageFmt     emFormat;             EImageFmt     emFormat;    // 图像格式
EDataAddrType emAddrType;           EDataAddrType emAddrType;  // 图像缓存地址类型
int nChannel;                       int nChannel;   // 通道数 mat.data 中的 channel()
int nHeight;                        int nHeight;
int nStride;                        int nStride;    // 每行字节数(d3d显示=pitch, ffmpeg解码=linesize, ffmpeg转码=stride)
int nWidth;                         int nWidth;
int nFrame;                         int nFrame;     // holcan专用
                    ------->        int nROINum;        // ROI 数量
                    ------->        TBbox* ROIInfo;     // 定义一个指向 TBbox 类型的指针，调用者 申请，由 调用者 释放
unsigned char* pbyBuffer;           unsigned char* pbyBuffer;  // 缓存由 调用者 申请，由 调用者 释放
}TImageInfo;                    }TImageInfo;
```


### 2.2 ROI预处理
#### 2.2.1 单张图基于单个ROI预处理接口设计
&emsp;&emsp; 单张图基于单个ROI预处理可以视为预处理中最原子的操作，支持 `CPU->CPU`、`CPU->GPU`、`GPU->GPU` 三种不同的数据流预处理，其中npp实现了 ROI Crop 和 resize 操作，只需要计算好裁剪坐标，就能crop并对resize ROI区域数据，能够加速大图裁剪时预处理，其基本流程如下图所示：
<center><img src="./images/预处理.jpg" style="width:100%"></center>
<center>图4. 单张图基于单个ROI预处理流程</center>


&emsp;&emsp; 此功能对应的，C++ API 接口函数为：
```C++
perImgPreprocessGPU(IN const TImageInfo& tInData,         // img and roi one to one preprocess
    IN const TBbox& tInROI,   // ROI info
    IN const TModelOpenParam& tOpenParam,
    IN Npp8u* &pu8SrcBuf,
    IN Npp8u* pu8ChannelConveredBuf,        // 颜色空间变换 BGR/RGB <-> GRAY
    IN Npp8u* pu8ResizedBuf,
    IN Npp32f* pf32NormBuf,
    IN Npp32f* pf32SplitBuf[3],
    IN size_t& nMaxSrcWidth,
    IN size_t& nMaxSrcHeight)
```


#### 2.2.2 大图裁剪推理预处理接口设计
&emsp;&emsp; 大图裁剪预处理需要在一张大图上对若干个ROI区域进行预处理，因此该函数接口参数为 `TImageInfo& tInData` 和 `std::vector<TBbox>& tInROI`，后者的长度为ROI的数量，最大值 `MAX_NUM_BATCH`。通过遍历 `tInROI`，对每个ROI区域进行预处理，然后将预处理后的数据拷贝到 `ptInputTensorArray` 中，进行后续模型推理，其接口参数如下所示：

```C++
// GPU
ImgPreprocessGPU(IN const TImageInfo& tInData,
    IN const std::vector<TBbox>& tInROI,   // ROI info
    IN const TModelOpenParam& tOpenParam,
    IN Npp8u*& pu8SrcBuf,
    IN Npp8u* pu8ChannelConveredBuf,
    IN Npp8u* pu8ResizedBuf,
    IN Npp32f* pf32NormBuf,
    IN Npp32f* pf32SplitBuf[3],
    IN size_t& nMaxSrcWidth,
    IN size_t& nMaxSrcHeight,
    OUT megaInfer::TArrayTensor* ptInputTensorArray)
```

#### 2.2.3 小图推理预处理接口设计
&emsp;&emsp; 小图预处理默认是在一张图上对一个ROI区域进行预处理，因此该函数接口参数为 `TBatchImageInfo& tInData` 和 `std::vector<TBbox>& tInROI`，并且两者的数量应该一致，最大值 `MAX_NUM_BATCH`。通过遍历 `tInData`，对每个图片进行预处理，然后将预处理后的数据拷贝到 `ptInputTensorArray` 中，进行后续模型推理，其接口参数如下所示：
```C++
ImgPreprocessGPU(IN const TBatchImageInfo& tInData,
    IN const std::vector<TBbox>& tInROI,   // ROI info
    IN const TModelOpenParam& tOpenParam,
    IN Npp8u*& pu8SrcBuf,
    IN Npp8u* pu8ChannelConveredBuf,
    IN Npp8u* pu8ResizedBuf,
    IN Npp32f* pf32NormBuf,
    IN Npp32f* pf32SplitBuf[3],
    IN size_t& nMaxSrcWidth,
    IN size_t& nMaxSrcHeight,
    OUT megaInfer::TArrayTensor* ptInputTensorArray)
```



### 2.3 目标检测
#### 2.3.1 目标检测异步推理结构设计如下
```
// 定义预处理和后处理数据队列，并设置最大队列长度
SafeQueue<TBbox> roiQueue;
roiQueue.set_max_size(1000);

SafeQueue<std::pair<std::vector<TBbox>, std::vector<cv::Mat>>> postQueue;
postQueue.set_max_size(1000);

// 定义结果存储容器
std::vector< std::future<EAIErrorCode> > results;

// 根据裁剪推理参数，判断是否需要裁剪推理
bool bSliceInfer = m_ptModelParam->iSliceHeight != 0 || m_ptModelParam->iSliceWidth != 0;

if (bSliceInfer)        // 大图裁剪推理
{
    // 启动
    roiQueue.start();
    postQueue.start();

    // 如果没有ROI信息，默认原图W，H作为ROI, 使用智能指针对 ROI 信息初始化
    if (CurrImageInfo.nROINum == 0)
    {
        CurrImageInfo.nROINum = 1;
        std::shared_ptr<TBbox*> roiInfo = std::make_shared<TBbox*>( new TBbox{ 0,0,CurrImageInfo.nWidth, CurrImageInfo.nHeight });
        CurrImageInfo.ROIInfo = *roiInfo;   
    }

    // 创建任务队列并放入线程池中。。
    // 任务1、预处理+推理（考虑支持大图缓存在GPU上，目前预处理也在GPU上实现，因此预处理和推理任务放在一个线程中完成）
    // 任务2、后处理
    results.emplace_back(m_detInferPool.commit(std::bind(&MegaDetectModel::asyncHandlePreAndInferSlice, this, std::ref(CurrImageInfo), std::ref(roiQueue), std::ref(postQueue))));
    results.emplace_back(m_detInferPool.commit(std::bind(&MegaDetectModel::asyncHandlePostprocessSlice, this, std::ref(postQueue), std::ref(detectinfos))));

    // 计算裁剪的坐标，只计算，不裁剪，将每个裁剪的坐标放入队列中，等待推理线程处理
    eRetErrCode = CalSlicePosition(CurrImageInfo, roiQueue);
    roiQueue.stop();

    // 等待所有线程任务完成，若出现错误，清空所有所有队列中未处理数据并停止队列和线程池，退出程序
    for (auto&& result : results) 
    {
        eRetErrCode = result.get();
        if (eRetErrCode != EAIErrorCode::AI_SUCCESS)
        {
            if (!roiQueue.empty())
            {
                roiQueue.clear();
            }
            roiQueue.stop();
            if (!postQueue.empty())
            {
                postQueue.clear();
            }
            postQueue.stop();
            m_detInferPool.stop();

            eRetErrCode = EAIErrorCode::AI_ERR_MODEL_INFERENCE;
            chErrMsg = "Async inference failed ! \n";
            SetLastErrorMessage(chErrMsg);
            return eRetErrCode;
        }
    }

    // 大图结果合并
    eRetErrCode = mergeDetectBox();
    eRetErrCode = unionDetectBox();
    eRetErrCode = filterDetectBox();

}
else        // 小图推理
{
    // 创建推理的ROI信息
    std::vector<TBbox> inferBatch;
    inferBatch.clear();
    for (auto idx_batch = 0; idx_batch < tInData.nNumImg; idx_batch++)
    {
        if (tInData.atImageBuffer[idx_batch].nROINum == 0)       // 对 tInData ROI 信息初始化
        {
            // 小图推理，如果没有传ROI信息，默认认为只有一个ROI，且为 {0,0,W,H};
            inferBatch.emplace_back(TBbox{ 0, 0, tInData.atImageBuffer[idx_batch].nWidth, tInData.atImageBuffer[idx_batch].nHeight });
        }
        else
        {
            // 如果有ROI信息，默认一个batch只有一个ROI，读取第 0 个ROI;
            inferBatch.emplace_back(TBbox{ tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopX,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopY,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nWidth,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nHeight });
        }

        // 预处理、推理、后处理顺序执行
    }
}
```

### 2.4 语义分割
&emsp;&emsp; 语义分割大图后处理比较复杂，对结果合并的逻辑比较复杂，因此语义分割的预处理、推理和后处理都在gpu上执行，因此只采用单线程的方式执行。
```
// 定义预处理队列，并设置最大队列长度
SafeQueue<TBbox> roiQueue;
roiQueue.set_max_size(1000);

// 定义结果存储容器
std::vector< std::future<EAIErrorCode> > results;

// 根据裁剪推理参数，判断是否需要裁剪推理
bool bSliceInfer = m_ptModelParam->iSliceHeight != 0 || m_ptModelParam->iSliceWidth != 0;

if (bSliceInfer)        // 大图裁剪推理
{
    // 启动
    roiQueue.start();

    // 如果没有ROI信息，默认原图W，H作为ROI, 使用智能指针对 ROI 信息初始化
    if (CurrImageInfo.nROINum == 0)
    {
        CurrImageInfo.nROINum = 1;
        std::shared_ptr<TBbox*> roiInfo = std::make_shared<TBbox*>( new TBbox{ 0,0,CurrImageInfo.nWidth, CurrImageInfo.nHeight });
        CurrImageInfo.ROIInfo = *roiInfo;   
    }

    // 根据设备类型，考虑后处理在GPU或是CPU的不同情况，需要分别在GPU或CPU上申请大图推理结果保存的内存
    if (0 == strcmp(m_ptModelParam->achDeviceType, "GPU"))
    {
        auto status = cudaMemset(m_pu8IdxResBuf, 0, (size_t)CurrImageInfo.nWidth * CurrImageInfo.nHeight);
        cudaDeviceSynchronize();
        status = cudaMemset(m_pu32ConfResBuf, 0, (size_t)CurrImageInfo.nWidth * CurrImageInfo.nHeight * sizeof(Npp32f));
        cudaDeviceSynchronize();
        results.emplace_back(m_segInferPool.commit(std::bind(&ISegmentation::asyncHandlePIP, this, std::ref(CurrImageInfo), std::ref(roiQueue))));
    }
    else
    {
        // 创建结果画布,存放最后拼接结果
        segMask = cv::Mat::zeros(cv::Size(CurrImageInfo.nWidth, CurrImageInfo.nHeight), CV_8U);
        segConf = cv::Mat::zeros(cv::Size(CurrImageInfo.nWidth, CurrImageInfo.nHeight), CV_32F);
        results.emplace_back(m_segInferPool.commit(std::bind(&ISegmentation::asyncHandlePIPWithCPU, this, std::ref(CurrImageInfo), std::ref(roiQueue), std::ref(segMask), std::ref(segConf))));
    }

    // 计算裁剪的坐标，只计算，不裁剪，将每个裁剪的坐标放入队列中，等待推理线程处理
    eRetErrCode = CalSlicePosition(CurrImageInfo, roiQueue);
    roiQueue.stop();

    // 等待所有线程任务完成，若出现错误，清空所有所有队列中未处理数据并停止队列和线程池，退出程序
    for (auto&& result : results) 
    {
        eRetErrCode = result.get();
        if (eRetErrCode != EAIErrorCode::AI_SUCCESS)
        {
            if (!roiQueue.empty())
            {
                roiQueue.clear();
            }
            roiQueue.stop();
            m_detInferPool.stop();

            eRetErrCode = EAIErrorCode::AI_ERR_MODEL_INFERENCE;
            chErrMsg = "Async inference failed ! \n";
            SetLastErrorMessage(chErrMsg);
            return eRetErrCode;
        }
    }

    // 大图结果合并拷贝到输出结构体中

}
else        // 小图推理
{
    // 创建推理的ROI信息
    std::vector<TBbox> inferBatch;
    inferBatch.clear();
    for (auto idx_batch = 0; idx_batch < tInData.nNumImg; idx_batch++)
    {
        if (tInData.atImageBuffer[idx_batch].nROINum == 0)       // 对 tInData ROI 信息初始化
        {
            // 小图推理，如果没有传ROI信息，默认认为只有一个ROI，且为 {0,0,W,H};
            inferBatch.emplace_back(TBbox{ 0, 0, tInData.atImageBuffer[idx_batch].nWidth, tInData.atImageBuffer[idx_batch].nHeight });
        }
        else
        {
            // 如果有ROI信息，默认一个batch只有一个ROI，读取第 0 个ROI;
            inferBatch.emplace_back(TBbox{ tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopX,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopY,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nWidth,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nHeight });
        }

        // 预处理、推理、后处理顺序执行
    }
}
```

### 2.5 稠密点定位
&emsp;&emsp; 稠密点定位和语义分割类似，后处理比较复杂，在gpu上可以实现更快的速度，因此稠密点定位的预处理、推理和后处理都在gpu上执行，所以只采用单线程的方式执行。
```
// 定义预处理队列，并设置最大队列长度
SafeQueue<TBbox> roiQueue;
roiQueue.set_max_size(1000);

// 定义结果存储容器
std::vector< std::future<EAIErrorCode> > results;

// 根据裁剪推理参数，判断是否需要裁剪推理
bool bSliceInfer = m_ptModelParam->iSliceHeight != 0 || m_ptModelParam->iSliceWidth != 0;

if (bSliceInfer)        // 大图裁剪推理
{
    // 启动
    roiQueue.start();

    // 如果没有ROI信息，默认原图W，H作为ROI, 使用智能指针对 ROI 信息初始化
    if (CurrImageInfo.nROINum == 0)
    {
        CurrImageInfo.nROINum = 1;
        std::shared_ptr<TBbox*> roiInfo = std::make_shared<TBbox*>( new TBbox{ 0,0,CurrImageInfo.nWidth, CurrImageInfo.nHeight });
        CurrImageInfo.ROIInfo = *roiInfo;   
    }

    // 向线程池中插入推理任务
    results.emplace_back(m_locateInferPool.commit(std::bind(&ILocation::asyncHandlePIP, this, std::ref(CurrImageInfo), std::ref(roiQueue), std::ref(nPointStartIdx), std::ref(detectinfos))));

    // 计算裁剪的坐标，只计算，不裁剪，将每个裁剪的坐标放入队列中，等待推理线程处理
    eRetErrCode = CalSlicePosition(CurrImageInfo, roiQueue);
    roiQueue.stop();

    // 等待所有线程任务完成，若出现错误，清空所有所有队列中未处理数据并停止队列和线程池，退出程序
    for (auto&& result : results) 
    {
        eRetErrCode = result.get();
        if (eRetErrCode != EAIErrorCode::AI_SUCCESS)
        {
            if (!roiQueue.empty())
            {
                roiQueue.clear();
            }
            roiQueue.stop();
            m_detInferPool.stop();

            eRetErrCode = EAIErrorCode::AI_ERR_MODEL_INFERENCE;
            chErrMsg = "Async inference failed ! \n";
            SetLastErrorMessage(chErrMsg);
            return eRetErrCode;
        }
    }

    // 大图结果合并拷贝到输出结构体中
    eRetErrCode = mergeDetectPoint()；
    eRetErrCode = unionDetectPoint();
    eRetErrCode = filterDetectPoint();

}
else        // 小图推理
{
    // 创建推理的ROI信息
    std::vector<TBbox> inferBatch;
    inferBatch.clear();
    for (auto idx_batch = 0; idx_batch < tInData.nNumImg; idx_batch++)
    {
        if (tInData.atImageBuffer[idx_batch].nROINum == 0)       // 对 tInData ROI 信息初始化
        {
            // 小图推理，如果没有传ROI信息，默认认为只有一个ROI，且为 {0,0,W,H};
            inferBatch.emplace_back(TBbox{ 0, 0, tInData.atImageBuffer[idx_batch].nWidth, tInData.atImageBuffer[idx_batch].nHeight });
        }
        else
        {
            // 如果有ROI信息，默认一个batch只有一个ROI，读取第 0 个ROI;
            inferBatch.emplace_back(TBbox{ tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopX,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopY,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nWidth,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nHeight });
        }

        // 预处理、推理、后处理顺序执行
    }
}
```

### 2.6 分类
&emsp;&emsp; 分类模块理论上不支持裁剪推理，此处的设计旨在从一张大图上Crop出若干了ROI区域进行分类处理，Crop的过程可以看作是一个特殊的裁剪操作，用户需要明白这个概念是和上面算法模块有所区别的。
```
// 定义预处理队列，并设置最大队列长度
SafeQueue<TBbox> roiQueue;
roiQueue.set_max_size(1000);

// 定义结果存储容器
std::vector< std::future<EAIErrorCode> > results;

// 根据传入的ROI数量判断是否需要根据 ROI 信息进行 crop 推理
bool bSliceInfer = tInputInfo.atImageBuffer[0].nROINum > 1;
if (bSliceInfer)        // crop出ROI推理
{
    // 启动
    roiQueue.start();

    // 如果没有ROI信息，默认原图W，H作为ROI, 使用智能指针对 ROI 信息初始化
    if (CurrImageInfo.nROINum == 0)
    {
        CurrImageInfo.nROINum = 1;
        std::shared_ptr<TBbox*> roiInfo = std::make_shared<TBbox*>( new TBbox{ 0,0,CurrImageInfo.nWidth, CurrImageInfo.nHeight });
        CurrImageInfo.ROIInfo = *roiInfo;   
    }

    // 向线程池中插入推理任务
    results.emplace_back(m_clsInferPool.commit(std::bind(&IClassifier::asyncHandleInferCrop, this, std::ref(CurrImageInfo), std::ref(roiQueue), std::ref(detectinfos))));

    // 分类的 SliceInfer 不是严格意义上的切片方式，而是根据传入的ROI进行crop
    for (int idxROI = 0; idxROI < CurrImageInfo.nROINum; idxROI++)
    {
        roiQueue.push(TBbox{ tInputInfo.atImageBuffer[idx_batch].ROIInfo[idxROI].nLeftTopX,
                                tInputInfo.atImageBuffer[idx_batch].ROIInfo[idxROI].nLeftTopY,
                                tInputInfo.atImageBuffer[idx_batch].ROIInfo[idxROI].nWidth,
                                tInputInfo.atImageBuffer[idx_batch].ROIInfo[idxROI].nHeight });
    }
    //delete CurrImageInfo.ROIInfo;
    roiQueue.stop();

    // 等待所有线程任务完成，若出现错误，清空所有所有队列中未处理数据并停止队列和线程池，退出程序
    for (auto&& result : results) 
    {
        eRetErrCode = result.get();
        if (eRetErrCode != EAIErrorCode::AI_SUCCESS)
        {
            if (!roiQueue.empty())
            {
                roiQueue.clear();
            }
            roiQueue.stop();
            m_detInferPool.stop();

            eRetErrCode = EAIErrorCode::AI_ERR_MODEL_INFERENCE;
            chErrMsg = "Async inference failed ! \n";
            SetLastErrorMessage(chErrMsg);
            return eRetErrCode;
        }
    }

    // 分类结果拷贝到输出结构体中
    eRetErrCode = mergeDetectPoint()；
    eRetErrCode = unionDetectPoint();
    eRetErrCode = filterDetectPoint();

}
else        // 小图推理
{
    // 创建推理的ROI信息
    std::vector<TBbox> inferBatch;
    inferBatch.clear();
    for (auto idx_batch = 0; idx_batch < tInData.nNumImg; idx_batch++)
    {
        if (tInData.atImageBuffer[idx_batch].nROINum == 0)       // 对 tInData ROI 信息初始化
        {
            // 小图推理，如果没有传ROI信息，默认认为只有一个ROI，且为 {0,0,W,H};
            inferBatch.emplace_back(TBbox{ 0, 0, tInData.atImageBuffer[idx_batch].nWidth, tInData.atImageBuffer[idx_batch].nHeight });
        }
        else
        {
            // 如果有ROI信息，默认一个batch只有一个ROI，读取第 0 个ROI;
            inferBatch.emplace_back(TBbox{ tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopX,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nLeftTopY,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nWidth,
                                            tInData.atImageBuffer[idx_batch].ROIInfo[0].nHeight });
        }

        // 预处理、推理、后处理顺序执行
    }
}
```