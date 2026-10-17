# libplacebo5

libplacebo 是一个可移植的视频渲染和颜色处理库（v5 系列），专注于提供高质量的视频播放体验。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [5.264.1](./5.264.1/) | built | 2026-09-16 |

## 描述

libplacebo5 是 libplacebo 上游项目的 v5 系列版本（与已归档的 libplacebo/7.349.0 为同一上游项目的不同大版本）。

主要功能：
- 高质量视频缩放和滤波
- 色彩空间转换和色调映射（HDR → SDR）
- 去隔行和去噪处理
- GLSL 着色器系统与代码生成
- GPU 后端抽象（OpenGL/Vulkan/D3D11，OHOS 上禁用）

## 编译状态

- 构建系统: meson（>= 0.63）
- 编译器: clang/clang++ 15.0.4
- 上游测试: 9/9 通过（meson test，纯 CPU 单元测试）
- 状态: built

## 依赖

- meson >= 0.63
- ninja

## 已知问题

### GPU 后端禁用

在鸿蒙系统上禁用了以下图形 API：
- OpenGL（-Dopengl=disabled）
- Vulkan（-Dvulkan=disabled）
- D3D11（-Dd3d11=disabled）
- glslang/shaderc（-Dglslang/-Dshaderc=disabled）

编译为有限功能版本：保留 GLSL 生成、色彩管理、tonemapping 等 CPU 侧能力（上游对无 GPU 构建有明确声明），渲染相关的 API 在 OHOS 上不可用。

### 上游 submodules 未打包

v5.264.1 tar.gz 的 3rdparty/ 为空的 git submodule 目录。实测无需补充：`src/vulkan/meson.build` 对 vulkan.h 的探测命中 OHOS SDK sysroot 自带头文件，其余 submodule 仅在对应 GPU 后端 enabled 时被引用（本配方全部 disabled）。

## 使用方式

```bash
# 使用预编译包（conan 制品仓）
conan install --requires=libplacebo5/5.264.1@ohpcd/stable

# 编译后链接
cc myapp.c $(pkg-config --cflags --libs libplacebo)
```

## 版本说明

- **5.264.1**: 首个鸿蒙适配版本，禁用 GPU 后端，编译为 CPU 功能版本；上游 9 项单元测试全部通过。