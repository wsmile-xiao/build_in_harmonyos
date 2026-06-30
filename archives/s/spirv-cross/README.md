# SPIRV-Cross - HarmonyOS 编译记录

## 概述

SPIRV-Cross 是 KhronosGroup 开发的 SPIR-V 着色器交叉编译器，支持将 SPIR-V 中间代码转换为 GLSL、HLSL、MSL（Metal）、C++ 等目标语言。它是 Vulkan SDK 的核心组件，广泛用于图形渲染引擎和 GPU 工具链。

**编译状态**: ✅ 成功（published）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 内核版本 | 1.12.0 |
| C 库 | musl libc |
| 编译器 | clang 15.0.4 |
| 构建系统 | CMake |
| 版本 | vulkan-sdk-1.4.341.0 |

## 编译步骤

```bash
# 1. 下载源码
curl -fsSL -o spirv-cross-1.4.341.0.tar.gz \
  https://github.com/KhronosGroup/SPIRV-Cross/archive/refs/tags/vulkan-sdk-1.4.341.0.tar.gz
tar xzf spirv-cross-1.4.341.0.tar.gz
cd SPIRV-Cross-vulkan-sdk-1.4.341.0

# 2. CMake 配置
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ ..

# 3. 编译
make -j2

# 4. 安装（DESTDIR模式，用于打包）
make install DESTDIR=$TEST_PREFIX

# 5. 本地安装（模拟用户部署）
make install
```

## 产物清单

### 可执行文件

| 文件 | 说明 |
|------|------|
| bin/spirv-cross | CLI 交叉编译工具（4.0M，支持GLSL/HLSL/MSL/反射/C++后端） |

### 静态库（8个）

| 文件 | 说明 |
|------|------|
| lib/libspirv-cross-core.a (1.0M) | 核心 IR 解析和 CFG 分析 |
| lib/libspirv-cross-glsl.a (2.4M) | GLSL / Vulkan GLSL 后端 |
| lib/libspirv-cross-hlsl.a (1.3M) | HLSL 后端 |
| lib/libspirv-cross-msl.a (3.4M) | Metal Shading Language 后端 |
| lib/libspirv-cross-cpp.a (225K) | C++ 后端（已标记 DEPRECATED） |
| lib/libspirv-cross-reflect.a (158K) | JSON 反射后端 |
| lib/libspirv-cross-util.a (21K) | 工具辅助库 |
| lib/libspirv-cross-c.a (190K) | C API 封装 |

### 头文件（17个）

`include/spirv_cross/` 目录下包含所有 C/C++ API 头文件，包括 C API (`spirv_cross_c.h`) 和 SPIR-V 定义 (`spirv.h`, `spirv.hpp`)。

### pkg-config

- `lib/pkgconfig/spirv-cross-c.pc`（版本号 0.68.0）

### CMake Config

8 个模块的 `spirv_cross_*Config.cmake` + `Config-release.cmake`，支持 `find_package()`。

## 功能验证结果

| 测试项 | 结果 |
|--------|------|
| spirv-cross --revision | ✅ 显示 Git commit 时间戳 |
| 默认 GLSL 后端 | ✅ 输出 #version 450 compute shader |
| Vulkan GLSL 后端 (-V) | ✅ 输出 descriptor set + push constant |
| MSL 后端 (--msl) | ✅ 输出 Metal kernel 函数 |
| HLSL 后端 (--hlsl) | ✅ 输出 cbuffer + SM5.0 |
| 反射后端 (--reflect) | ✅ 输出 JSON entryPoints + types |
| C++ 后端 (--cpp) | ✅ 输出 C++ 类代码 |
| pkg-config --modversion | ✅ 0.68.0 |
| pkg-config --libs/--cflags | ✅ 路径正确 |
| 静态库 8 个完整性 | ✅ 全部包含正确对象文件 |
| C API 头文件编译 | ✅ spvc_context_create 编译通过 |
| 头文件 17 个安装 | ✅ 全部完整 |

## 适配特点

- **零适配**：无需任何源码修改或补丁，直接编译成功
- CMake 显示 "System is unknown to cmake" 警告，但不影响编译器检测和构建结果
- 所有产物为静态库(.a)和CLI工具，无动态库(.so)
- 官方测试套件需要 glslang/SPIRV-Tools，standalone 构建不包含

## 注意事项

- 版本号有两个体系：vulkan-sdk tag (1.4.341.0) 和 pkg-config 内部版本 (0.68.0)
- 静态库链接顺序：-lspirv-cross-c 依赖 -lspirv-cross-core、-lspirv-cross-glsl、-lspirv-cross-util
- 平台 lld 链接器缺失 libxml2.so.16，手动链接 C API 静态库受限（不影响 CMake 构建）