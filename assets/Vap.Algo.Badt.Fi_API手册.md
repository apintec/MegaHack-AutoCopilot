# Vap.Algo.Badt.Fi — API 使用手册

> 程序集：`Vap.Algo.Badt.Fi.dll`  
> 目标框架：`netstandard2.1`  
> 依赖：`HalconDotNet`（halcondotnetxl.dll v21.5）、`Microsoft.Extensions.Logging.Abstractions`

---

## 目录

1. [整体架构](#1-整体架构)
2. [核心类与接口](#2-核心类与接口)
   - 2.1 [IAlgoBase — 算法接口](#21-ialgobase--算法接口)
   - 2.2 [BaseInspectionAlgo — 抽象基类](#22-baseinspectionalgo--抽象基类)
   - 2.3 [BaseAlgoInput — 算法输入](#23-basealgoinput--算法输入)
   - 2.4 [BaseAlgoParam — 算法参数](#24-basealgoparam--算法参数)
   - 2.5 [BaseAlgoResult / SingleDefect — 算法输出](#25-basealgoresult--singledefect--算法输出)
3. [枚举说明](#3-枚举说明)
   - 3.1 [RESULT_TYPE](#31-result_type)
   - 3.2 [AlgoModule](#32-algomodule)
   - 3.3 [DefectType](#33-defecttype)
4. [Attribute 体系](#4-attribute-体系)
   - 4.1 [AlgoModuleAttribute](#41-algomoduleattribute)
   - 4.2 [PropertyEditorAttribute](#42-propertyeditorattribute)
   - 4.3 [辅助 Attribute（CheckBox / TextBox / NumericUpDown）](#43-辅助-attribute)
5. [算法执行流程](#5-算法执行流程)
6. [直接调用示例（强类型）](#6-直接调用示例强类型)
7. [反射调用示例（动态发现与执行）](#7-反射调用示例动态发现与执行)
   - 7.1 [发现所有算法模块](#71-发现所有算法模块)
   - 7.2 [通过反射读取参数元数据](#72-通过反射读取参数元数据)
   - 7.3 [通过反射执行算法](#73-通过反射执行算法)
8. [图像输入说明](#8-图像输入说明)
   - 8.1 [HALCON HObject 方式](#81-halcon-hobject-方式)
   - 8.2 [原始字节数组方式（非 HALCON 环境）](#82-原始字节数组方式非-halcon-环境)
9. [新增算法模块指南](#9-新增算法模块指南)
10. [已支持算法模块清单](#10-已支持算法模块清单)
11. [DefectType 完整列表](#11-defecttype-完整列表)

---

## 1. 整体架构

```
Vap.Algo.Badt.Fi
├── Base/
│   ├── IAlgoBase<TInput,TParam,TResult>      # 算法顶层接口
│   ├── BaseInspectionAlgo<TInput,TParam,TResult> # 抽象基类（日志、异常封装）
│   ├── BaseAlgoInput                          # 输入基类（图像 + ROI）
│   ├── BaseAlgoParam                          # 参数基类（开关、路径、分辨率）
│   └── BaseAlgoResult / SingleDefect          # 结果基类（缺陷列表）
├── Attributes/
│   ├── AlgoModuleAttribute                    # 标注算法类所属模块
│   └── PropertyEditorAttribute + 辅助 Attr   # 参数 UI 元数据
├── Common/
│   ├── AlgoModule / DefectType / RESULT_TYPE  # 枚举
│   ├── NRect / ROIRect                        # 坐标结构
│   └── CommonFunc                             # HALCON 图像转换工具
├── AIExport/
│   ├── AIInterface                            # P/Invoke 层（调用 native DLL）
│   └── CommonStruct / ModelParams             # native 结构体定义
└── Detect<XXX>/
    ├── InspectionAlgo   : BaseInspectionAlgo  # 具体算法实现
    ├── InspectionInput  : BaseAlgoInput        # 算法专属输入（可为空继承）
    ├── InspectionParam  : BaseAlgoParam        # 算法专属参数
    └── InspectionResult : BaseAlgoResult       # 算法专属结果（可为空继承）
```

---

## 2. 核心类与接口

### 2.1 IAlgoBase — 算法接口

```csharp
namespace Vap.Algo.Badt.Fi.Base

public interface IAlgoBase<TInput, TParam, TResult> : IDisposable
    where TInput  : BaseAlgoInput
    where TParam  : BaseAlgoParam
    where TResult : BaseAlgoResult
{
    void        Init(TParam param);
    RESULT_TYPE Run(TInput input, TParam param, out TResult result);
}
```

| 方法 | 说明 |
|------|------|
| `Init(param)` | 加载 AI 模型、初始化推理句柄。每次参数（ModelPath）变更后需重新调用。 |
| `Run(input, param, out result)` | 对图像执行推理。参数支持运行期动态修改（阈值等），无需重新 Init。 |
| `Dispose()` | 释放 native 推理句柄，必须在算法生命周期结束时调用（建议 `using`）。 |

---

### 2.2 BaseInspectionAlgo — 抽象基类

```csharp
public abstract class BaseInspectionAlgo<TInput, TParam, TResult>
    : IAlgoBase<TInput, TParam, TResult>
    where TInput  : BaseAlgoInput
    where TParam  : BaseAlgoParam
    where TResult : BaseAlgoResult, new()
{
    protected readonly ILogger Logger;

    protected BaseInspectionAlgo(ILogger logger = null);  // 可选注入日志

    // 公开（框架层）
    public void        Init(TParam param);                // 封装 OnInit，统一日志/异常
    public RESULT_TYPE Run(TInput input, TParam param, out TResult result);

    // 子类实现
    protected abstract void         OnInit(TParam param);
    protected abstract RESULT_TYPE  OnRun(TInput input, TParam param, TResult result);
}
```

`BaseInspectionAlgo` 在 `Init`/`Run` 公开方法中统一处理：
- 记录入参日志（模型路径、图像尺寸）
- 捕获异常并写入 `result.ErrMsg`，返回 `RESULT_TYPE.ERROR`
- 子类只需聚焦业务逻辑（`OnInit` / `OnRun`）

---

### 2.3 BaseAlgoInput — 算法输入

```csharp
namespace Vap.Algo.Badt.Fi.Base

public class BaseAlgoInput : IDisposable
{
    public HObject       SrcImg    { get; set; }  // HALCON 图像对象（灰度或彩色）
    public ROIRect       RoiRect   { get; set; }  // 检测 ROI（null = 全图）
    public List<ROIRect> ShieldRois { get; set; } // 屏蔽区域列表

    // 从灰度字节数组创建 HALCON 图像（内部 CopyImage，调用方无需保持缓冲区存活）
    public void SetImageFromGrayBytes(byte[] grayData, int width, int height);

    public void Dispose();  // 释放 SrcImg
}
```

**ROIRect 结构**

```csharp
public class ROIRect
{
    public double LeftTopX, LeftTopY, RightBottomX, RightBottomY { get; set; }
    public double Width  => RightBottomX - LeftTopX;
    public double Height => RightBottomY - LeftTopY;
    public bool   IsEmpty { get; }
}
```

---

### 2.4 BaseAlgoParam — 算法参数

```csharp
namespace Vap.Algo.Badt.Fi.Base

[AddINotifyPropertyChangedInterface]   // 自动实现 INotifyPropertyChanged
public class BaseAlgoParam
{
    public bool   EnableDetect { get; set; } = true;   // 算法总开关
    public string ModelPath    { get; set; } = "";     // AI 模型 JSON 路径
    public double ResolutionX  { get; set; } = 15;     // 相机 X 分辨率（um/pixel）
    public double ResolutionY  { get; set; } = 15;     // 相机 Y 分辨率（um/pixel）
}
```

各算法在自己的 `InspectionParam` 中继承并扩展专属阈值参数。所有参数属性均标注了 `[PropertyEditor]` 等 Attribute，供 UI 框架通过反射自动生成编辑控件。

---

### 2.5 BaseAlgoResult / SingleDefect — 算法输出

```csharp
public class BaseAlgoResult
{
    public List<SingleDefect> Defects { get; set; }  // 检测到的缺陷列表
    public string             ErrMsg  { get; set; }  // 错误信息（仅 ERROR 时非空）
}

public class SingleDefect
{
    public DefectType DefectType   { get; set; }  // 缺陷类型（枚举）
    public NRect      DefectRect   { get; set; }  // 缺陷像素坐标矩形
    public double     DefectConf   { get; set; }  // 置信度 [0, 1]
    public double     DefectWidth  { get; set; }  // 缺陷宽度（单位 mm）
    public double     DefectHeight { get; set; }  // 缺陷高度（单位 mm）
    public double     Length       { get; set; }  // 缺陷长度（单位 mm，划伤专用）
}
```

**NRect 结构**

```csharp
public class NRect
{
    public int LeftTopX, LeftTopY, RightBottomX, RightBottomY { get; set; }
    public int  Width  => RightBottomX - LeftTopX;
    public int  Height => RightBottomY - LeftTopY;
    public bool IsEmpty { get; }
}
```

> **注意**：`DefectWidth`/`DefectHeight` 由算法内部完成换算（`像素数 × ResolutionX/Y ÷ 1000`），调用方直接读取 mm 值，无需二次换算。

---

## 3. 枚举说明

### 3.1 RESULT_TYPE

```csharp
namespace Vap.Algo.Badt.Fi.Base

public enum RESULT_TYPE { OK, NG, ERROR }
```

| 值 | 含义 |
|----|------|
| `OK` | 检测通过，无超阈值缺陷 |
| `NG` | 检测不通过，`result.Defects` 非空 |
| `ERROR` | 运行时异常，查看 `result.ErrMsg` |

---

### 3.2 AlgoModule

```csharp
namespace Vap.Algo.Badt.Fi.Common

public enum AlgoModule
{
    [Description("FPB/PCB类缺陷检测")]      FPC_PCB_DEFECT         = 1,
    [Description("POL类不良缺陷检测")]      POL_DEFECT             = 2,
    [Description("保护膜不良缺陷检测")]     PROTECTIVE_FILM_DEFECT = 3,
    [Description("Tape不良缺陷检测")]       TAPE_DEFECT            = 4,
    [Description("易撕贴缺陷检测")]         PULL_TAB_DEFECT        = 5,
    [Description("破损（Panel）缺陷检测")]  PANEL_DAMAGE_DEFECT    = 6,
    [Description("胶类不良缺陷检测")]       ADHESIVE_RESIDUE_DEFECT= 7,
    [Description("CG盖板类缺陷检测")]       COVER_GLASS_DEFECT     = 8,
    [Description("背光类不良缺陷检测")]     BACKLIGHT_DEFECT       = 9,
}
```

通过 `[Description]` 获取中文名称：

```csharp
var desc = typeof(AlgoModule)
    .GetField(module.ToString())
    ?.GetCustomAttribute<DescriptionAttribute>()
    ?.Description ?? module.ToString();
```

---

### 3.3 DefectType

`DefectType` 枚举包含 50+ 成员，均标注 `[Description("中文名称")]`。  
获取中文名称方式同 `AlgoModule`，参见 [§11 完整列表](#11-defecttype-完整列表)。

---

## 4. Attribute 体系

### 4.1 AlgoModuleAttribute

```csharp
[AttributeUsage(AttributeTargets.Class, AllowMultiple = false, Inherited = false)]
public sealed class AlgoModuleAttribute : Attribute
{
    public AlgoModule Module { get; }
    public AlgoModuleAttribute(AlgoModule module);
}
```

用于标注算法类所属的功能模块，配合反射实现算法自动发现：

```csharp
// 标注示例
[AlgoModule(AlgoModule.PROTECTIVE_FILM_DEFECT)]
public class InspectionAlgo : BaseInspectionAlgo<...> { }

// 反射发现
var module = typeof(InspectionAlgo)
    .GetCustomAttribute<AlgoModuleAttribute>()?.Module;
```

---

### 4.2 PropertyEditorAttribute

```csharp
[AttributeUsage(AttributeTargets.Property)]
public sealed class PropertyEditorAttribute : Attribute
{
    public string    DisplayName { get; set; }  // 参数显示名称
    public string    Description { get; set; }  // 参数描述（Tooltip）
    public int       TitleWidth  { get; set; }  // UI 标题栏宽度（px）
    public EditorType EditorType { get; set; }  // 编辑器类型（见下表）
}

public enum EditorType { CheckBox, TextBox, NumericUpDown, ComboBox, ColorPicker, DateTimePicker }
```

---

### 4.3 辅助 Attribute

| Attribute | 适用 EditorType | 关键属性 |
|-----------|----------------|---------|
| `[CheckBox]` | CheckBox | 无额外属性 |
| `[TextBox(Watermark, BrowseMode, FileFilter)]` | TextBox | `BrowseMode`: None/Folder/File；`FileFilter`: 对话框过滤器 |
| `[NumericUpDown(Minimum, Maximum, Increment, Precision)]` | NumericUpDown | 数值范围和步进 |

**使用示例**：

```csharp
[PropertyEditor(DisplayName = "气泡置信度阈值", TitleWidth = 120,
                Description = "置信度卡控阈值", EditorType = EditorType.NumericUpDown)]
[NumericUpDown(Minimum = 0, Maximum = 1, Increment = 0.01, Precision = 2)]
public double BubbleConfTh { get; set; } = 0.25;

[PropertyEditor(DisplayName = "模型路径", TitleWidth = 120,
                EditorType = EditorType.TextBox)]
[TextBox(BrowseMode = BrowseMode.File, FileFilter = "JSON 模型文件|*.json|所有文件|*.*")]
public string ModelPath { get; set; } = "";
```

---

## 5. 算法执行流程

```
┌──────────────────────────────────────────────────────────────┐
│  调用方                                                        │
│                                                               │
│  1. 构造参数对象  InspectionParam param = new() { ... }       │
│  2. 构造算法实例  using var algo = new InspectionAlgo(logger) │
│  3. 初始化模型    algo.Init(param)         ← 加载 .json 模型  │
│  4. 构造输入      var input = new InspectionInput            │
│                   input.SrcImg = hImage   ← HALCON 图像      │
│  5. 执行推理      var ret = algo.Run(input, param, out result)│
│  6. 处理结果      foreach defect in result.Defects { ... }   │
│  7. 资源释放      algo.Dispose() / using 自动释放             │
└──────────────────────────────────────────────────────────────┘

Init 内部流程：
  OnInit(param)
    ├─ 验证 ModelPath 文件存在
    ├─ setupDetectorLogLevel()
    ├─ parseJsonToOpenParam()   ← 解析模型配置 JSON
    └─ createDetectorHandle()  ← 创建 native 推理句柄

Run 内部流程：
  Run(input, param, out result)
    ├─ 读取图像尺寸并记录日志
    └─ OnRun(input, param, result)
         ├─ EnableDetect == false → 直接返回 OK
         ├─ ConvertFVObjectToTImageInfo_Gray() ← HALCON → native 格式
         ├─ inferDetectorAnalysis()            ← native 推理
         └─ 遍历检测框 → 过滤阈值 → 填充 result.Defects
              DefectWidth  = wPx × ResolutionX / 1000  (mm)
              DefectHeight = hPx × ResolutionY / 1000  (mm)
```

---

## 6. 直接调用示例（强类型）

```csharp
using HalconDotNet;
using Microsoft.Extensions.Logging;
using Vap.Algo.Badt.Fi.Base;
using PF = Vap.Algo.Badt.Fi.DetectProtectiveFilm;

// 1. 构造日志（可选）
using var loggerFactory = LoggerFactory.Create(b =>
{
    b.SetMinimumLevel(LogLevel.Debug);
    b.AddConsole();
});

// 2. 构造参数
var param = new PF.InspectionParam
{
    ModelPath     = @"D:\models\bubble\hslp.json",
    ResolutionX   = 15.0,   // um/pixel
    ResolutionY   = 15.0,
    EnableDetect  = true,
    IsCheckBubble = true,
    BubbleConfTh  = 0.25,
    BubbleWidthTh = 10,
    BubbleHeightTh= 10,
};

// 3. 读取图像（HALCON）
HOperatorSet.ReadImage(out HObject hImage, @"D:\images\sample.bmp");

try
{
    // 4. 创建算法实例并初始化
    using var algo = new PF.InspectionAlgo(
        loggerFactory.CreateLogger<PF.InspectionAlgo>());
    algo.Init(param);

    // 5. 构造输入并执行
    using var input = new PF.InspectionInput { SrcImg = hImage };
    var ret = algo.Run(input, param, out PF.InspectionResult result);

    // 6. 处理结果
    Console.WriteLine($"结果: {ret}，缺陷数: {result.Defects.Count}");
    foreach (var defect in result.Defects)
    {
        var r = defect.DefectRect;
        Console.WriteLine(
            $"  {defect.DefectType}  置信度:{defect.DefectConf:F2}  " +
            $"[{r.LeftTopX},{r.LeftTopY}~{r.RightBottomX},{r.RightBottomY}]  " +
            $"{defect.DefectWidth:F2}×{defect.DefectHeight:F2}mm");
    }
}
finally
{
    hImage.Dispose();
}
```

---

## 7. 反射调用示例（动态发现与执行）

### 7.1 发现所有算法模块

```csharp
using System.ComponentModel;
using System.Reflection;
using Vap.Algo.Badt.Fi.Attributes;
using Vap.Algo.Badt.Fi.Base;
using Vap.Algo.Badt.Fi.Common;

var assembly = typeof(BaseAlgoParam).Assembly;

// 找出所有标注了 [AlgoModule] 的类，按模块 ID 排序
var algoTypes = assembly.GetTypes()
    .Where(t => t.GetCustomAttribute<AlgoModuleAttribute>() != null)
    .OrderBy(t => (int)t.GetCustomAttribute<AlgoModuleAttribute>().Module);

foreach (var algoType in algoTypes)
{
    var module = algoType.GetCustomAttribute<AlgoModuleAttribute>().Module;

    // 读取 AlgoModule 的 [Description] 中文名
    var moduleDesc = typeof(AlgoModule)
        .GetField(module.ToString())
        ?.GetCustomAttribute<DescriptionAttribute>()
        ?.Description ?? module.ToString();

    // 查找同命名空间下的 InspectionParam
    var paramType = assembly.GetType(algoType.Namespace + ".InspectionParam");

    Console.WriteLine($"[{(int)module}] {moduleDesc}");
    Console.WriteLine($"    AlgoType  = {algoType.FullName}");
    Console.WriteLine($"    ParamType = {paramType?.FullName}");
}
```

---

### 7.2 通过反射读取参数元数据

```csharp
// 按继承层级顺序枚举属性（基类属性在前）
static IEnumerable<PropertyInfo> GetOrderedProperties(Type type)
{
    var hierarchy = new List<Type>();
    for (var t = type; t != null && t != typeof(object); t = t.BaseType)
        hierarchy.Insert(0, t);
    return hierarchy.SelectMany(t =>
        t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly));
}

var paramInstance = Activator.CreateInstance(paramType);  // 使用默认值

foreach (var prop in GetOrderedProperties(paramType))
{
    var editor = prop.GetCustomAttribute<PropertyEditorAttribute>();
    if (editor == null) continue;

    var numAttr  = prop.GetCustomAttribute<NumericUpDownAttribute>();
    var textAttr = prop.GetCustomAttribute<TextBoxAttribute>();

    Console.WriteLine($"  [{editor.EditorType}] {editor.DisplayName}");
    Console.WriteLine($"    属性名   = {prop.Name}");
    Console.WriteLine($"    描述     = {editor.Description}");
    Console.WriteLine($"    当前值   = {prop.GetValue(paramInstance)}");

    if (numAttr != null)
        Console.WriteLine($"    范围     = [{numAttr.Minimum}, {numAttr.Maximum}]，步进={numAttr.Increment}，精度={numAttr.Precision}");
    if (textAttr?.BrowseMode != BrowseMode.None)
        Console.WriteLine($"    浏览模式 = {textAttr.BrowseMode}，过滤器={textAttr.FileFilter}");
}
```

**输出示例（DetectProtectiveFilm）：**

```
  [CheckBox]      算法总开关
    属性名 = EnableDetect,  当前值 = True
  [TextBox]       模型路径
    属性名 = ModelPath,     浏览模式 = File，过滤器 = JSON 模型文件|*.json|...
  [NumericUpDown] 图像X分辨率(um/pixel)
    属性名 = ResolutionX,   范围=[1, 100]，步进=0.01，精度=2
  [NumericUpDown] 图像Y分辨率(um/pixel)
    属性名 = ResolutionY,   范围=[1, 100]，步进=0.01，精度=2
  [CheckBox]      检测气泡
    属性名 = IsCheckBubble, 当前值 = True
  [NumericUpDown] 气泡置信度阈值
    属性名 = BubbleConfTh,  范围=[0, 1]，步进=0.01，精度=2
  [NumericUpDown] 气泡宽度阈值(px)
    属性名 = BubbleWidthTh, 范围=[0, 10000]，步进=1，精度=0
  [NumericUpDown] 气泡高度阈值(px)
    属性名 = BubbleHeightTh,范围=[0, 10000]，步进=1，精度=0
```

---

### 7.3 通过反射执行算法

> **适用场景**：插件系统、UI 框架（VisionUI）等在编译期不知道具体算法类型的场景。

```csharp
// 前提：algoType 为具体算法类（如 DetectProtectiveFilm.InspectionAlgo）
//       paramInstance 为对应的 InspectionParam 实例（已设置好参数）
//       algoInstance  为已完成 Init 的算法实例（object 类型）

// ── 构造输入 ──────────────────────────────────────────────────────
var inputType = algoType.Assembly.GetType(algoType.Namespace + ".InspectionInput")
                ?? typeof(BaseAlgoInput);
using var input = (BaseAlgoInput)Activator.CreateInstance(inputType);

// 方式 A：HALCON 图像
input.SrcImg = hImage;

// 方式 B：非 HALCON 环境（WPF BitmapSource → 灰度字节数组）
//   var gray = new FormatConvertedBitmap(bitmapSource, PixelFormats.Gray8, null, 0);
//   var data = new byte[gray.PixelWidth * gray.PixelHeight];
//   gray.CopyPixels(data, gray.PixelWidth, 0);
//   input.SetImageFromGrayBytes(data, gray.PixelWidth, gray.PixelHeight);

// ── 调用 Run ──────────────────────────────────────────────────────
// 签名：RESULT_TYPE Run(TInput input, TParam param, out TResult result)
var runMethod = algoType.GetMethod("Run");
var args = new object[] { input, paramInstance, null };  // args[2] = out result
var retVal = (RESULT_TYPE)runMethod.Invoke(algoInstance, args);
var result = (BaseAlgoResult)args[2];

// ── 处理结果 ──────────────────────────────────────────────────────
Console.WriteLine($"结果: {retVal}，缺陷数: {result.Defects.Count}");
foreach (var defect in result.Defects)
{
    // 获取 DefectType 中文名
    var desc = typeof(DefectType)
        .GetField(defect.DefectType.ToString())
        ?.GetCustomAttribute<DescriptionAttribute>()
        ?.Description ?? defect.DefectType.ToString();

    var r = defect.DefectRect;
    Console.WriteLine(
        $"  {desc}({defect.DefectType})  " +
        $"置信度:{defect.DefectConf:F2}  " +
        $"[{r.LeftTopX},{r.LeftTopY}~{r.RightBottomX},{r.RightBottomY}]  " +
        $"{defect.DefectWidth:F2}×{defect.DefectHeight:F2}mm");
}
```

> **注意**：`out` 参数在反射调用中通过 `args[2]` 返回，调用前传入 `null` 占位。

---

## 8. 图像输入说明

### 8.1 HALCON HObject 方式

算法原生接受 `HObject`（HALCON 图像对象），支持灰度（1通道）和彩色（3通道）。内部通过 `CommonFunc.ConvertFVObjectToTImageInfo_Gray / _RGB` 转换为 native 格式后送入推理引擎。

```csharp
HOperatorSet.ReadImage(out HObject hImage, @"path/to/image.bmp");
var input = new InspectionInput { SrcImg = hImage };
```

### 8.2 原始字节数组方式（非 HALCON 环境）

无 HALCON 环境（如 WPF UI 层）时，使用 `SetImageFromGrayBytes` 从灰度字节数组创建 HObject：

```csharp
// 以 WPF BitmapSource 为例
var gray = src.Format == PixelFormats.Gray8
    ? src
    : new FormatConvertedBitmap(src, PixelFormats.Gray8, null, 0);
var data = new byte[gray.PixelWidth * gray.PixelHeight];
gray.CopyPixels(data, gray.PixelWidth, 0);

using var input = (BaseAlgoInput)Activator.CreateInstance(inputType);
input.SetImageFromGrayBytes(data, gray.PixelWidth, gray.PixelHeight);
// 调用完毕后 input.Dispose() 自动释放 SrcImg
```

`SetImageFromGrayBytes` 内部调用 `HOperatorSet.GenImage1` + `CopyImage`，数据被复制到 HALCON 管理内存，调用方字节数组可在方法返回后立即释放。

---

## 9. 新增算法模块指南

1. **定义枚举值**：在 `EnumCollection.cs` 的 `AlgoModule` 中添加新成员并标注 `[Description]`。

2. **创建命名空间目录**：`Detect<XXX>/`，包含四个文件：

```
InspectionAlgo.cs   ← 继承 BaseInspectionAlgo，标注 [AlgoModule(AlgoModule.XXX)]
InspectionInput.cs  ← 继承 BaseAlgoInput（无额外字段时保持空继承）
InspectionParam.cs  ← 继承 BaseAlgoParam，添加专属阈值参数（标注 Attribute）
InspectionResult.cs ← 继承 BaseAlgoResult（无额外字段时保持空继承）
```

3. **实现 OnInit 和 OnRun**：

```csharp
[AlgoModule(AlgoModule.XXX_DEFECT)]
public class InspectionAlgo
    : BaseInspectionAlgo<InspectionInput, InspectionParam, InspectionResult>
{
    public InspectionAlgo(ILogger<InspectionAlgo> logger = null) : base(logger) { }

    protected override void OnInit(InspectionParam param)
    {
        // 验证 ModelPath，调用 AIInterface 加载模型
    }

    protected override RESULT_TYPE OnRun(
        InspectionInput input, InspectionParam param, InspectionResult result)
    {
        if (!param.EnableDetect) return RESULT_TYPE.OK;
        // 推理逻辑，填充 result.Defects
        // DefectWidth/Height = px * Resolution / 1000（mm）
        return result.Defects.Count > 0 ? RESULT_TYPE.NG : RESULT_TYPE.OK;
    }
}
```

4. **添加参数**：

```csharp
public class InspectionParam : BaseAlgoParam
{
    [PropertyEditor(DisplayName = "置信度阈值", TitleWidth = 120,
                    Description = "检测置信度卡控阈值", EditorType = EditorType.NumericUpDown)]
    [NumericUpDown(Minimum = 0, Maximum = 1, Increment = 0.01, Precision = 2)]
    public double ConfTh { get; set; } = 0.5;
}
```

5. **验证**：新算法无需修改任何上层代码，VisionUI 通过反射自动发现并展示该模块。

---

## 10. 已支持算法模块清单

| ID | AlgoModule | 中文名 | 命名空间 |
|----|-----------|--------|---------|
| 1 | FPC_PCB_DEFECT | FPB/PCB类缺陷检测 | DetectFpcPcb |
| 2 | POL_DEFECT | POL类不良缺陷检测 | DetectPol |
| 3 | PROTECTIVE_FILM_DEFECT | 保护膜不良缺陷检测 | DetectProtectiveFilm |
| 4 | TAPE_DEFECT | Tape不良缺陷检测 | DetectTap |
| 5 | PULL_TAB_DEFECT | 易撕贴缺陷检测 | DetectPullTab |
| 6 | PANEL_DAMAGE_DEFECT | 破损（Panel）缺陷检测 | DetectPanelDamage |
| 7 | ADHESIVE_RESIDUE_DEFECT | 胶类不良缺陷检测 | DetectAdhesiveResidue |
| 8 | COVER_GLASS_DEFECT | CG盖板类缺陷检测 | DetectCoverGlass |
| 9 | BACKLIGHT_DEFECT | 背光类不良缺陷检测 | DetectBacklight |

---

## 11. DefectType 完整列表

| 枚举名 | 中文名 |
|--------|--------|
| ConnectorPoorConnection | 连接器-插接不良 |
| FpcReleaseFilmNotRemoved | FPC离型膜-离型膜未撕 |
| PcbCopperExposure | PCB-PCB漏铜 |
| PcbScratch | PCB划伤 |
| PcbComponentMissing | PCB元器件缺失 |
| PolDent | POL凹痕 |
| PolBump | POL凸点 |
| PolLifting | POL翘起 |
| PolMisalignment | POL错位 |
| ProtectiveFilmForeignMaterial | 保护膜异物 |
| ProtectiveFilmBubble | 保护膜气泡 |
| ProtectiveFilmLifting | 保护膜翘起 |
| ProtectiveFilmAdhesiveResidue | 保护膜残胶 |
| ProtectiveFilmStain | 保护膜污渍 |
| ProtectiveFilmScratch | 保护膜划伤 |
| TapeBulge | Tape凸起 |
| TapeWrinkle | Tape褶皱 |
| TapeOpen | Tape open |
| TapeLifting | Tape翘起 |
| TapeWhitening | Tape磨白 |
| TapeDamage | Tape破损 |
| PullTabMisalignment | 易撕贴偏位 |
| Crack | 裂纹 |
| CfEdgeChipping | CF边崩裂 |
| TftEdgeChipping | TFT边崩裂 |
| CornerChipping | 角Chipping |
| Burr | 毛刺 |
| PcbFrontAndBackAdhesive | PCB正胶/背胶 |
| PcbAdhesiveOverflow | PCB溢胶 |
| UvAdhesive | UV胶 |
| TuffyAdhesive | Tuffy胶 |
| TuffyAndIcEdgeAdhesiveDeficiency | Tuffy与IC下边缘视觉缺胶 |
| OilPrintResidue | 油印残留 |
| OilPrintOuterEdgeJaggedDefect | 油印外边缘锯齿状缺陷 |
| OilPrintInnerEdgeJaggedDefect | 油印内边缘锯齿状缺陷 |
| OilPrintVoidAndLightLeakage | 油印空洞和漏光 |
| OilPrintCenterMisalignmentTolerance | 油印中心偏位公差 |
| EdgeChip | 边Chip |
| CornerChip | 角Chip |
| Bulge | 凸起 |
| FpcCrease | FPC压/折痕 |
| BackplateDeformation | 背板变形 |
| MetalFrameDeformation | 铁框变形 |
| BackplateScratch | 背板划伤 |
| BlForeignMaterial | B/L异物 |
| BlStandFailure | B/L柱脚不良 |
| BlStain | B/L污渍 |
| BackplateIndentation | 背板压痕 |
| BackplatePaintPeeling | 背板掉漆 |
| BackplateUnevenSurface | 背板凹凸点 |
| BackplateDiscoloration | 背板异色 |
