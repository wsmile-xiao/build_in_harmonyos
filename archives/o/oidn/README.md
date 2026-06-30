# OpenImageDenoise (oidn)

OpenImageDenoise 是 Intel 开发的高性能图像降噪库，专为光线追踪渲染器设计，利用深度学习技术实现快速、高质量的降噪。

## 功能概述

- **CPU 降噪**：利用 ISPC 编译的 SIMD 优化的神经网络推理
- **GPU 降噪**：支持 CUDA、HIP、SYCL 等多种 GPU 后端
- **RT Filter**：专为光线追踪渲染优化的降噪滤波器
- **RTLightmap Filter**：用于光照贴图的降噪
- **高质量输出**：保留细节的同时有效去除噪声

## OHOS 适配要点

### 已解决问题

1. **musl libc 兼容性**
   - 替换 `pthread_getaffinity_np/setaffinity_np` 为 `sched_getaffinity/sched_setaffinity`
   - 补丁：`0002-core-thread.cpp.patch`

2. **平台架构检测**
   - OIDN_ARCH 自动检测失效，需手动指定 `-DOIDN_ARCH=ARM64`
   - 补丁：`0001-cmake-oidn_platform.cmake.patch`

3. **ISPC 编译器**
   - 需要手动编译 ISPC 1.30.0（依赖 LLVM 18+）
   - 系统 LLVM 15 不满足要求

### 遗留问题

1. **预训练权重缺失**
   - Git LFS 权重文件（~80-150MB）网络下载困难
   - 需要在有 Git LFS 环境的机器上获取后传输

2. **运行时限制**
   - CPU device 初始化需要预训练神经网络权重
   - 缺少权重时 `oidnIsCPUDeviceSupported()` 返回 0

## 依赖关系

### 编译依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| TBB | 2021.13.0 | Intel Threading Building Blocks |
| ISPC | 1.30.0 | Intel SPMD Program Compiler |
| LLVM | 18.1.8 | 用于 ISPC 编译 |

### 运行依赖

- libc++_shared.so（OHOS SDK 提供）
- libtbb.so

## 编译配置

```cmake
cmake -B build \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DOIDN_DEVICE_CPU=ON \
  -DOIDN_ARCH:STRING=ARM64 \
  -DOIDN_FILTER_RT=OFF \
  -DOIDN_FILTER_RTLIGHTMAP=OFF \
  -DOIDN_APPS=OFF \
  -DTBB_ROOT=$DEFAULT_PREFIX \
  -DISPC_EXECUTABLE=$DEFAULT_PREFIX/bin/ispc
```

## 功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 库加载 | ✅ PASS | RPATH 已配置 |
| API 调用 | ✅ PASS | 符号导出正确 |
| CPU device | ⚠️ PARTIAL | 需真实权重才能初始化 |
| RT Filter | ⚠️ PARTIAL | 权重占位 |
| RTLightmap | ⚠️ PARTIAL | 权重占位 |

## 参考资料

- 官网：https://openimagedenoise.github.io
- GitHub：https://github.com/OpenImageDenoise/oidn
- 文档：https://github.com/OpenImageDenoise/oidn/blob/main/readme.pdf