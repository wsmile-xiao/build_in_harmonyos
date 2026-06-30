# OpenCV

**Open Source Computer Vision Library** — 开源计算机视觉库，提供数百种计算机视觉算法。

## 功能概述

- **核心模块**: core（基础数据结构）、imgproc（图像处理）、imgcodecs（图像编解码）
- **视觉模块**: calib3d（相机标定）、features2d（特征检测）、video（视频分析）
- **高级模块**: dnn（深度神经网络）、stitching（图像拼接）、objdetect（目标检测）

## OHOS 适配要点

### 关键问题
1. **处理器检测失败**: CMake 在 OpenHarmony 上检测处理器为 'unknown'（而非 aarch64），导致 libpng NEON 定义未正确添加
2. **NEON 链接错误**: ARM NEON 优化函数未链接，需手动禁用

### 解决方案
修改 `3rdparty/libpng/CMakeLists.txt`：
```cmake
add_definitions(-DPNG_ARM_NEON_OPT=0)
```

CMake 配置选项：
```bash
-DENABLE_NEON:BOOL=OFF
-DPNG_ARM_NEON:BOOL=OFF
-DCPU_BASELINE_DISABLE=NEON
```

### 已知限制
- 不支持 CUDA/OpenCL（移动平台）
- 部分 GUI 功能受限（无完整窗口系统）

## 依赖关系

### 编译依赖
- cmake >= 3.10
- clang >= 15.0
- Python >= 3.2（构建脚本）

### 运行依赖
- zlib
- libpng
- libjpeg（可选）
- ffmpeg（可选，视频 I/O）

## 参考资料

- 官网: https://opencv.org
- 源码: https://github.com/opencv/opencv
- 文档: https://docs.opencv.org