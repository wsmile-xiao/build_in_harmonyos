# WebAssembly Micro Runtime (WAMR)

## 简介

WebAssembly Micro Runtime (WAMR) 是一个轻量级、独立的 WebAssembly 运行时，由 Bytecode Alliance 开发和维护。它提供了 WebAssembly 模块的加载、解释执行和 AOT（Ahead-of-Time）编译执行能力。

## 主要功能

- **解释器**：快速解释执行 WebAssembly 模块
- **AOT 编译器**：将 WebAssembly 模块编译为本地机器码，提升执行性能
- **JIT 编译器**：支持 LLVM ORC JIT 和 Fast JIT
- **WASI 支持**：完整的 WebAssembly System Interface 支持
- **多平台支持**：支持 Linux、Windows、MacOS、Android 等多种平台
- **嵌入式友好**：适合在嵌入式设备和 IoT 场景中使用

## OHOS 适配要点

### 平台检测问题

WAMR 通过 `CMAKE_HOST_SYSTEM_NAME` 检测平台，在 HarmonyOS 上会检测到 "HarmonyOS"，但 WAMR 没有对应的平台支持代码。必须通过以下参数强制使用 Linux 平台配置：

```bash
cmake .. -DWAMR_BUILD_PLATFORM=linux
```

### 架构检测问题

WAMR 默认在 64 位平台上构建为 X86_64 目标，即使实际架构是 AARCH64。在 HarmonyOS (aarch64) 上编译时，必须明确指定目标架构：

```bash
cmake .. -DWAMR_BUILD_TARGET=AARCH64
```

### 完整编译命令

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DWAMR_BUILD_PLATFORM=linux \
  -DWAMR_BUILD_TARGET=AARCH64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF
make -j1
make install DESTDIR=<staging_dir>
```

### 库特性

WAMR 是一个运行时库，不是独立的命令行工具。编译产物是静态库 `libiwasm.a`，需要链接到应用程序中使用。主要的 API 头文件包括：

- `wasm_c_api.h`：WebAssembly 标准 C API
- `wasm_export.h`：WAMR 扩展 API
- `lib_export.h`：库导出定义

## 依赖关系

- **编译依赖**：无外部库依赖，内置所有必要的组件
- **运行依赖**：标准 C 库

## 已知限制

- 不支持 HarmonyOS 的原生平台特性（通过 Linux 平台配置适配）
- 测试套件需要单独构建和运行
- 部分高级特性（如 LLVM ORC JIT）可能需要额外的配置

## 参考资料

- 官方仓库：https://github.com/bytecodealliance/wasm-micro-runtime
- 文档：https://github.com/bytecodealliance/wasm-micro-runtime/blob/main/doc/
- WASI 规范：https://github.com/WebAssembly/WASI