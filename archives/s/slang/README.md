# slang - Slang 着色器语言编译器

## 软件概述

Slang 是一个高性能着色器语言编译器，由 NVIDIA 开发，支持 HLSL/Slang 到 SPIR-V/GLSL/HLSL 等多种目标的编译。它提供模块化编程、接口、泛型等高级特性，广泛应用于图形渲染领域。

### 主要功能

1. **着色器编译**：
   - 支持 HLSL/Slang 语言输入
   - 输出 SPIR-V、GLSL、HLSL 等多种目标格式
   - 支持模块化和接口编程

2. **命令行工具**：
   - `slangc` - 着色器编译器命令行工具
   - `slangi` - 交互式 REPL

3. **C/C++ API**：
   - `spGetBuildTagString()` - 获取构建标签
   - `slang::createGlobalSession()` - 创建全局会话
   - `slang::ISession` - 编译会话管理

### 应用场景

- 图形渲染管线编译
- 游戏引擎着色器预处理
- 实时图形 API 集成
- 跨平台着色器交叉编译

## 版本信息

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2026.14 | ✅ built | 2026-07-27 | 静态库构建，含5个平台兼容性补丁 |

## 依赖关系

无外部依赖，仅需系统库：
- clang/clang++ 15.0.4（C++20 编译器）

## 编译产物

### 2026.14 版本

**库文件**：
- `lib/libslang-compiler.a` - 主编译器库
- `lib/libslang-cpp-parser.a` - C++ 解析器库
- `lib/libcompiler-core.a` - 编译器核心库
- `lib/libcore.a` - 核心库
- `lib/libslang-rt.a` - 运行时库

**头文件**：
- `include/slang.h` - 主头文件
- `include/slang-com-pch.h` - COM 兼容头文件

**可执行文件**：
- `bin/slangc` - 着色器编译器命令行工具

## 使用方法

### CMake 集成

```cmake
find_package(slang REQUIRED)
target_link_libraries(your_target slang::slang)
```

### 命令行编译示例

```bash
slangc shader.slang -o shader.spirv -target spirv
```

### C API 示例

```cpp
#include <slang.h>

int main() {
    slang::IGlobalSession* globalSession = nullptr;
    slang::createGlobalSession(&globalSession);
    // ... use session for compilation
    globalSession->release();
    return 0;
}
```

## 相关资源

- **官方仓库**：https://github.com/shader-slang/slang
- **文档**：https://shader-slang.com/
- **许可证**：MIT

## 更新历史

- **2026-07-27**: 适配 2026.14 版本，支持 HarmonyOS PC 平台

---

**维护者**: openharmony-compile-agent
**最后更新**: 2026-07-27
