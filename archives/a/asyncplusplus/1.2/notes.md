# asyncplusplus 1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-20
- 编译器: clang-15 (Clang 15.0.4, /storage/Users/currentUser/usr/local/bin/clang-15)
- Conan profile: ohos-local (OHOS 6.0, armv8, Release, libc++)
- 状态: ✅ 真机验证通过

## 源码分析

asyncplusplus 是 Amanieu d'Antras 开发的轻量级 C++11/14 并发框架，提供：
- 任务调度（task scheduler）
- 任务续延（continuation via `.then()`）
- parallel_for / parallel_invoke / parallel_reduce
- 工作窃取队列（work-stealing queue）

源码结构极简：
- `src/`: 2 个 .cpp（scheduler.cpp, threadpool_scheduler.cpp）+ 4 个内部头文件
- `include/`: 1 个主头文件 `async++.h` + 15 个子头文件

## 依赖

| 依赖 | 类型 | 状态 |
|------|------|------|
| pthreads | 系统内置 | ✅ 可用 |

无外部依赖。纯 C++11 + pthreads。

## W0 依赖检查

asyncplusplus 无外部 Conan 包依赖，仅需系统 pthreads（OHOS 内置）。W0 通过。

## OHOS 适配方式

- cmake_minimum_required: 3.1 → 3.5（在 build() 中用 Python 替换，patch 上下文行号不一致）
- BUILD_SHARED_LIBS=OFF（静态库，通过 CMakeToolchain 注入）
- USE_CXX_EXCEPTIONS=ON（默认）
- CMake target 名: `Async++`（非 `Async++::Async++`）

## 上游测试

上游仓库**无测试套件**（无 `tests/` 目录，无 CTest targets）。
测试覆盖由 Conan test_package（L1）提供，包含 4 个实质性测试：
1. task_spawn — 基本任务创建和 get()
2. continuation — `.then()` 续延链
3. parallel_for — 并行遍历容器（100 元素）
4. parallel_invoke — 并行调用 3 个 callable

## 真机构建结果

```
======== Testing the package: Executing test ========
asyncplusplus/1.2@ohpcd/stable (test package): Running test()
asyncplusplus/1.2@ohpcd/stable (test package): RUN: ./test_asyncplusplus
asyncplusplus 1.2 test_package:
  PASS: task_spawn
  PASS: continuation
  PASS: parallel_for
  PASS: parallel_invoke
All 4 tests passed.
```

### 交付物

| 文件 | 说明 |
|------|------|
| libasync++.a | 静态库 |
| include/async++.h | 主头文件 |
| include/async++/*.h | 15 个子头文件 |
| cmake/Async++Config.cmake | CMake find_package 支持 |

### 构建注意事项

- OHOS 真机 CMake 报 `System is unknown to cmake, create Platform/HarmonyOS` 是正常警告，不影响构建
- OHOS 真机 mkfifo 报 `Operation not permitted` 是 make jobserver 警告，构建正常完成
- 编译器 `-Wl,--code-sign` / `-fuse-ld=lld` / `-L...` 在编译阶段产生 unused argument 警告，属于 profile LDFLAGS 泄漏，无影响

## CMake 特性

- `cmake_minimum_required(VERSION 3.1)` → Python 替换为 3.5
- `BUILD_SHARED_LIBS` 选项（默认 ON，Conan 配方设为 OFF）
- `USE_CXX_EXCEPTIONS` 选项（默认 ON）
- 编译选项包含 `-fno-rtti`（OHOS clang 支持）
- 安装 CMake config: `Async++Config.cmake` → `find_package(Async++)`
- CMake target: `Async++`

## issue

待补（需在项目 issue tracker 创建）

---

**适配结束**: 2026-08-20
**最终状态**: published（真机验证通过，4/4 测试全通过）
