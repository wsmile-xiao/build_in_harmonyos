# glslang

## 简介

glslang 是 OpenGL 和 OpenGL ES 的着色器前端和验证器，支持：
- GLSL (OpenGL Shading Language)
- ESSL (OpenGL ES Shading Language)
- HLSL (High-Level Shading Language)
- SPIR-V 输出

它是 Vulkan SDK 的核心组件之一，用于着色器编译和验证。

## 版本信息

- **版本**: vulkan-sdk-1.3.290.0
- **发布日期**: 2024-06-26
- **Vulkan SDK 版本**: 1.3.290.0

## 构建信息

### 依赖

**构建依赖**:
- CMake >= 3.17.2
- GCC/G++ 或 Clang/Clang++
- Python 3 (用于测试)

**运行时依赖**:
- spirv-tools (可选，用于 SPIR-V 优化)

### 构建系统

- **类型**: CMake
- **选项**:
  - `CMAKE_INSTALL_PREFIX`: 安装路径
  - `CMAKE_BUILD_TYPE`: 构建类型 (Release/Debug)
  - `ALLOW_EXTERNAL_SPIRV_TOOLS`: 使用外部 SPIRV-Tools
  - `ENABLE_OPT`: 启用 SPIR-V 优化
  - `BUILD_SHARED_LIBS`: 构建共享库

### 可执行文件

- `glslang`: 着色器编译器
- `spirv-remap`: SPIR-V 重映射工具

### 库文件

- `libglslang.a`: 核心库
- `libSPIRV.a`: SPIR-V 支持
- `libSPVRemapper.a`: SPIR-V 重映射
- `libMachineIndependent.a`: 平台无关前端（启用 HLSL 时包含 HLSL 源码）
- `libOSDependent.a`: 平台相关实现
- `libGenericCodeGen.a`: 通用代码生成
- `libglslang-default-resource-limits.a`: 默认资源限制实现

此版本不会生成或安装独立的 `libHLSL.a`。

## 使用示例

```bash
# 编译 GLSL 着色器为 SPIR-V
glslang -V shader.vert -o shader.vert.spv

# 验证着色器
glslang -l shader.frag

# 编译 HLSL 着色器
glslang -D -V shader.hlsl -o shader.spv
```

## 许可证

BSD 3-Clause License

## 链接

- 官方仓库: https://github.com/KhronosGroup/glslang
- Vulkan SDK: https://vulkan.lunarg.com/
- 规范文档: https://www.khronos.org/opengl/
