# Leptonica

## 简介

Leptonica 是一个开源的图像处理和图像分析库，提供了丰富的图像操作功能，包括图像读取/写入、几何变换、形态学运算、边缘检测、阈值处理、条码识别等。

## 功能概述

- **图像 I/O**：支持 BMP、JPEG、PNG、TIFF、GIF、WebP 等多种格式（本构建仅启用 BMP 和原生格式，可选图像库已禁用）
- **几何变换**：缩放、旋转、平移、投影变换
- **形态学运算**：腐蚀、膨胀、开运算、闭运算
- **图像增强**：对比度调整、直方图处理、锐化
- **分割与识别**：阈值处理、连通域分析、条码识别
- **图像合成**：混合、拼接、叠加

## OHOS 适配

### 适配要点

1. **CMake 版本兼容性**：需设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 解决旧版 CMakeLists.txt 兼容问题
2. **构建系统选择**：autogen.sh 失败（libtoolize shebang 路径错误），改用 cmake 构建
3. **可选图像库禁用**：通过 `CMAKE_DISABLE_FIND_PACKAGE_*` 禁用 PNG/JPEG/TIFF/GIF/WebP/OpenJPEG，仅链接 zlib，避免符号冲突
4. **静态库编译**：默认编译为静态库 `libleptonica.a`

### 已知问题

- 源码中的 CMakeLists.txt 版本较旧，需要兼容性参数
- cmake 警告 "System is unknown"（鸿蒙不在 cmake 已知平台列表中），可忽略
- 若启用 JPEG 支持会遇到符号未定义链接错误，当前选择禁用

## 依赖

### 编译依赖

- zlib（唯一 Conan 依赖，通过 `zlib/1.3.1@ohpcd/stable` 引入）

### 可选依赖（当前已禁用）

以下依赖可通过移除 `CMAKE_DISABLE_FIND_PACKAGE_*` 启用，但当前构建未启用：

- libpng (PNG 格式支持)
- libjpeg-turbo (JPEG 格式支持)
- libtiff (TIFF 格式支持)
- libwebp (WebP 格式支持)
- openjpeg (JPEG 2000 支持)
- giflib (GIF 格式支持)

## 功能验证

```bash
# Conan 构建
conan create archives/l/leptonica/1.87.0/ --user=ohpcd --channel=stable \
  -pr:b=default -pr:h=default --build=missing

# CI 验证（L0-L5 全通过）
CI_PACKAGES="archives/l/leptonica/1.87.0" zsh ci/conan/build_and_test.sh

# test_package 输出
# leptonica version: leptonica-1.87.0
```

## 参考

- 官方仓库：https://github.com/DanBloomberg/leptonica
- 文档：http://www.leptonica.org/
