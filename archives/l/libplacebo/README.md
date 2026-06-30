# libplacebo

libplacebo 是一个用于视频播放和处理的可移植库，提供高质量的视频渲染和颜色处理功能。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [7.349.0](./7.349.0/) | built | 2026-05-21 |

## 描述

libplacebo（简称 "libplacebo"）是一个可移植、可重用的视频渲染和颜色处理库，专注于提供高质量的视频播放体验。

主要功能：
- 高质量视频缩放和滤波（支持多种算法）
- 色彩空间转换和色调映射（HDR → SDR）
- 去隔行和去噪处理
- 视频处理流水线抽象
- 支持多种 GPU 后端（OpenGL、Vulkan、D3D11）
- 基于 GLSL 的着色器系统

## 编译状态

- 鸿蒙难度: 🟡 (中等)
- 构建系统: meson
- 编译器: clang 15.0.4

## 依赖

- meson >= 1.11.1
- ninja >= 1.12.1
- Vulkan headers（系统自带）

## 已知问题

### Git Submodule 缺失

**问题**: 原始 tar.gz 包不包含 git submodule 内容（fast_float）

**影响**:
- G0 干净构建验证无法通过（违反 R21 和 R22）
- 无法从原始源码干净构建

**解决方案**:
手动下载 fast_float v6.1.6 到 `3rdparty/fast_float/include/fast_float/` 目录：
```bash
cd libplacebo-v7.349.0/3rdparty/fast_float
mkdir -p include/fast_float
curl -L https://github.com/fastfloat/fast_float/archive/refs/tags/v6.1.6.tar.gz -o fast_float.tar.gz
tar xzf fast_float.tar.gz --strip-components=3 -C include/fast_float fast_float-6.1.6/include/fast_float
```

**预编译包可用性**:
预编译包功能完整可用，可正常使用。

### 图形 API 禁用

在鸿蒙系统上禁用了以下图形 API：
- OpenGL（缺少 glad loader）
- Vulkan（可选）
- D3D11（不适用）
- glslang/shaderc（可选）

编译为有限功能版本，主要用于：
- 颜色空间转换
- 视频处理算法
- CPU 端视频处理流水线

## 使用方式

```bash
# 使用预编译包（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libplacebo 7.349.0

# 编译后链接
gcc myapp.c $(pkg-config --cflags --libs libplacebo)
```

## 版本说明

- **7.349.0**: 首个鸿蒙适配版本，禁用图形 API，编译为有限功能版本