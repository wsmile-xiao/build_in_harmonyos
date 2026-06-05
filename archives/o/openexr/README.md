# OpenEXR

OpenEXR 是由 Industrial Light & Magic 开发的高动态范围（HDR）图像文件格式，用于存储高精度图像数据。

## 功能概述

- **HDR 图像格式**: 支持 16-bit 半精度和 32-bit 浮点像素深度
- **无损压缩**: 支持多种压缩算法（PIZ, ZIP, RLE, PXR24, B44, B44A, DWAA, DWAB）
- **多通道**: 支持任意数量的图像通道
- **多层图像**: 支持多层图像存储（用于合成和后期制作）
- **元数据**: 支持丰富的元数据存储（属性、摄像机参数等）

## OHOS 适配要点

### 依赖关系
- **IlmBase**: 必需依赖，包含 Half（半精度浮点）、Imath（数学库）、Iex（异常处理）、IlmThread（线程库）
- **zlib**: 压缩算法依赖

### 编译注意事项
1. **IlmBase 依赖**: 需要先编译安装 IlmBase，确保 pkg-config 能找到 IlmBase.pc
2. **静态链接表生成**: b44ExpLogTable 和 dwaLookups 需要使用静态库重新链接，避免动态链接问题
3. **ELF 签名**: 鸿蒙系统要求动态链接库必须经过 ELF 签名才能加载和执行
4. **平台识别**: 可能需要更新 config.guess/config.sub 以支持 HarmonyOS 平台

### 已知问题
- 动态链接问题：在鸿蒙系统上，动态链接库需要 ELF 筠名才能被加载器识别
- RUNPATH 设置：即使设置了正确的 RUNPATH，未签名的库仍无法加载

## 编译依赖

```
IlmBase 2.2.1+ (必需)
zlib 1.2.11+ (可选，用于压缩)
```

## 运行依赖

```
IlmBase (动态链接需要 ELF 签名)
```

## 参考资料

- 官网: https://www.openexr.com
- GitHub: https://github.com/AcademySoftwareFoundation/openexr
- 文档: https://openexr.readthedocs.io