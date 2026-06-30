# Leptonica

## 简介

Leptonica 是一个开源的图像处理和图像分析库，提供了丰富的图像操作功能，包括图像读取/写入、几何变换、形态学运算、边缘检测、阈值处理、条码识别等。

## 功能概述

- **图像 I/O**：支持 BMP、JPEG、PNG、TIFF、GIF、WebP 等多种格式
- **几何变换**：缩放、旋转、平移、投影变换
- **形态学运算**：腐蚀、膨胀、开运算、闭运算
- **图像增强**：对比度调整、直方图处理、锐化
- **分割与识别**：阈值处理、连通域分析、条码识别
- **图像合成**：混合、拼接、叠加

## OHOS 适配

### 适配要点

1. **CMake 版本兼容性**：需要设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 解决旧版 CMakeLists.txt 兼容问题
2. **依赖库路径**：需要通过 `CMAKE_PREFIX_PATH` 或 `EXTRAINCLUDES/EXTRALIBS` 指定依赖库位置
3. **静态库编译**：默认编译为静态库 `libleptonica.a`

### 已知问题

- 源码中的 CMakeLists.txt 版本较旧，需要兼容性参数
- 结构体对齐警告（bmpio.c 中的 packed member 地址问题）
- 部分可选依赖（TIFF、WebP、OpenJPEG）需要额外配置

## 依赖

### 编译依赖

- zlib
- libpng
- libjpeg-turbo

### 可选依赖

- libtiff (TIFF 格式支持)
- libwebp (WebP 格式支持)
- openjpeg (JPEG 2000 支持)
- giflib (GIF 格式支持)

## 功能验证

```bash
# 验证静态库存在
ls ~/usr/local/lib/libleptonica.a

# 验证头文件
ls ~/usr/local/include/leptonica/allheaders.h

# 使用 pkg-config 验证（如果有）
pkg-config --modversion lept_Release
```

## 参考

- 官方仓库：https://github.com/DanBloomberg/leptonica
- 文档：http://www.leptonica.org/