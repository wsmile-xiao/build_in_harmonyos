# backward-cpp

backward-cpp 是一个 C++ 栈回溯（stacktrace）打印库，在错误/调试场景下打印人类可读的调用栈，支持异常堆栈、信号处理与崩溃回溯。

## 简介

- 头文件库（header-only）：核心为单个 `backward.hpp`
- 功能：捕获当前调用栈、解析符号（dladdr）、美化打印
- 支持：异常（`Traceable` 异常基类）、信号（SIGSEGV 等）、多线程
- 上游: https://github.com/bombela/backward-cpp （MIT License）

## OpenHarmony 适配说明

- **Dl_info 不可见**：OHOS dlfcn.h 仅在 `_GNU_SOURCE`/`_BSD_SOURCE` 下暴露 `Dl_info`，且默认构建（无 BFD/DWARF）下 backward.hpp 未包含 dlfcn.h → 补丁先定义宏再 include（`0002-backward.hpp.patch`）
- **program_invocation_name 缺失**：OHOS musl 无 glibc 扩展符号，测试框架改用 `__progname`（`0003-test-_test_main.cpp.patch`）
- **CMake 兼容**：`cmake_minimum_required` 3.0 → 3.5（CMake 4.x 移除 <3.5 兼容，`0001-CMakeLists.txt.patch`）
- 构建系统：CMake，header-only，无外部依赖，产物仅 `backward.hpp` + `BackwardConfig.cmake`
