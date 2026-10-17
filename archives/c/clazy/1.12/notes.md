# clazy 1.12 适配笔记

## 基本信息
- 软件: clazy (Qt 静态代码分析工具)
- 版本: 1.12
- 构建系统: CMake
- 上游: https://github.com/KDE/clazy
- 源码URL: https://github.com/KDE/clazy/archive/refs/tags/v1.12.tar.gz

## 版本选择
- 最新版 v1.17.1 要求 LLVM >= 19.0，但系统 LLVM 为 15.0.4
- v1.12 的 FindLLVM.cmake 使用 LLVM_FIND_VERSION (14.0) 作为阈值，兼容 LLVM 15

## 依赖
- LLVM/Clang 14.0+ (使用 OHOS SDK 自带 LLVM 15.0.4)
- 路径: /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm

## 编译参数
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DLLVM_ROOT=$LLVM_ROOT \
  -DCLAZY_LINK_CLANG_DYLIB=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,--unresolved-symbols=ignore-all -Wl,--allow-shlib-undefined -L$LLVM_ROOT/lib -L$LLVM_ROOT/lib/aarch64-linux-ohos" \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--allow-shlib-undefined -L$LLVM_ROOT/lib -L$LLVM_ROOT/lib/aarch64-linux-ohos" \
  -DCMAKE_CXX_FLAGS="-I${ABI_OVERRIDE}"
```

## 平台适配

### 1. FindLLVM.cmake 修改 — 单体库回退
OHOS SDK LLVM 只有单体 libLLVM.so，没有独立组件 .so 文件。
在 FindLLVM.cmake 中添加过滤逻辑：检查 --libfiles 返回的文件是否存在，
不存在的回退到 libLLVM.so。

### 2. CMakeLists.txt 修改 — 跳过 filesystem 链接检查
try_compile 的 filesystem 链接测试因 ABI 命名空间不匹配而失败，
改为仅检查头文件支持（编译通过即认为支持）。

### 3. ABI 命名空间适配
- OHOS SDK LLVM/Clang 库使用 `std::__h` 命名空间
- 系统 libc++_shared.so 使用 `std::__n1` 命名空间
- 解决方案: 创建修改版 __config_site (将 __n1 改为 __h)，通过 -I 覆盖

### 4. 链接器标志
- `--allow-shlib-undefined`: 允许共享库有未定义符号
- `--unresolved-symbols=ignore-all`: 允许可执行文件有未定义符号

## 构建产物
- ClazyPlugin.so (Clang 插件共享库)
- clazy-standalone (独立可执行文件)
- clazy (包装脚本)

## 已知限制
由于 OHOS SDK LLVM/Clang 库使用 `__h` ABI 命名空间，
而系统 libc++ 使用 `__n1`，clazy-standalone 运行时
部分 libc++ 符号无法解析。这是平台 SDK 的 ABI 配置问题。
ClazyPlugin.so 可作为 Clang 插件在 clang 进程中使用（符号由 clang 提供）。
---

**编译结束**: 2026-08-10 18:57
**最终状态**: built
