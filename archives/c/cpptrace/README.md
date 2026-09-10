# cpptrace

cpptrace（jeremy-rifkin/cpptrace）是一个轻量、可移植的 C++11 栈追踪库：
生成堆栈追踪并解析符号（函数名、文件名、行号），支持异常追踪
（`cpptrace::logic_error` 等）、内联帧展开与自由格式的 trace 对象 API。

## 功能概述

- `cpptrace::generate_trace()` / `generate_raw_trace()` / `generate_object_trace()`：栈追踪生成
- 符号化后端：libdwarf（本配方启用）；备选 addr2line / libdl / dbghelp
- unwind 后端：libgcc unwind（`_Unwind_Backtrace`，本配方启用）
- demangle 后端：cxxabi（libc++abi）
- C API（`ctrace/ctrace.h`）与 C++ API 双入口
- 零外部运行时依赖（符号化依赖 libdwarf+zstd+zlib，由 Conan 管理）

## OHOS 适配要点

1. **平台识别**：CMake 无 HarmonyOS 平台模块，`CMAKE_SYSTEM_NAME=Linux`
   强制走 UNIX 分支；否则上游 autoconfig 误选 dbghelp（Windows 后端）。
2. **unwind tables**：OHOS musl 下默认优化不发射 `.eh_frame`，库与测试
   编译需 `-funwind-tables`（已实测：不带则 `backtrace`/`_Unwind_Backtrace`
   返回 0 帧）。
3. **外置依赖**：`CPPTRACE_USE_EXTERNAL_LIBDWARF/ZSTD/GTEST=ON` +
   `CPPTRACE_CONAN=ON`，全部依赖来自制品仓（libdwarf/0.11.1 →
   zlib/1.3.1 + zstd/1.5.6；gtest/1.17.0），无 FetchContent 网络访问。
4. **无源码补丁**：上游原生支持上述全部开关。

## 依赖关系

- 编译/运行：libdwarf/0.11.1（传递 zlib/1.3.1、zstd/1.5.6）
- 测试（test_requires）：gtest/1.17.0

## 已知限制

- CXX20 module 变体（`unittest_module` 等）需 Clang≥16 + C++20，
  OHOS clang 15 / C++17 profile 下不实例化（按平台限制豁免）。

## 参考资料

- 上游仓库：https://github.com/jeremy-rifkin/cpptrace
- 上游文档：https://github.com/jeremy-rifkin/cpptrace/blob/main/docs.md
