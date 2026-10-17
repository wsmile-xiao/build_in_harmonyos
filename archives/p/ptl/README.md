# PTL

PTL (Parallel Tasking Library) is a lightweight C++11 multithreading tasking system that provides thread pools, task groups, asynchronous tasks, and an optional oneTBB backend.

## 功能概述

- 提供可配置的线程池与任务队列
- 支持异步任务、递归任务和任务组归并
- 支持原生线程后端与 oneTBB 后端
- 提供 CMake 包配置和 `PTL::ptl` 消费目标

## HarmonyOS 适配

- 使用 OHOS clang/clang++ 和 Conan CMake 工具链构建。
- 保留并执行上游 6 个示例测试，包括原生线程与 TBB 两条路径。
- 修复上游 `Backtrace.hh` 缺少 `<cstring>`、导致现代 C++ 编译器无法解析 `strlen` 的问题。
- 通过能力检测在 HarmonyOS 上由工作线程调用 `sched_setaffinity`，保留 CPU 亲和性行为。

## 依赖关系

- `tbb/2023.0.0.1`
- HarmonyOS 系统线程库

## 参考资料

- 上游仓库：https://github.com/jrmadsen/PTL
- 上游版本：https://github.com/jrmadsen/PTL/releases/tag/v2.3.3
