# mathic — Groebner 基快数据结构库

## 概述

mathic（Macaulay2/mathic，LGPL-2.0-or-later）是 Macaulay2 / Frobby 生态的
C++ 快数据结构库，为 Groebner 基计算提供 S-pair 优先级队列、除数查询与
多项式项排序原语。数据结构全部模板化，可接入调用方自己的单项式表示；
库内仅测试与示例代码自带单项式定义。

**本仓库适配版本**：1.4（HarmonyOS PC aarch64）

## 功能概述

- `mathic::BitTriangle`：三角位矩阵（列动态增长，`bit`/`bitUnordered`/`setBit`）
- `mathic::HashTable<Conf>`：模板哈希表（`insert`/`lookup`/`remove`，节点句柄）
- `mathic::PairQueue<Conf>`：S-pair 优先级队列（按列入列、`pop` 有序出列）
- `mathic::KDTree` / `DivList` / `DivFinder`：除数查询结构
- `mathic::TourTree` / `StlSet` / `Heap` / `Geobucket`：候选队列后端
- CLI 包：`Action` / `CliParser` / `BoolParameter` / `IntegerParameter` 等
- C 探测符号 `libmathicIsPresent()` + 版本串 `MATHIC_VERSION_STRING=="1.4"`

## OHOS 适配要点

1. **构建走 CMake**：上游另有 autotools，本包只走 CMake（与同生态
   memtailor/1.4 一致，便于复用其 gtest/ctest 修复经验）。
2. **memtailor 依赖走 Conan 而非系统路径**：上游 `cmake/FindMemtailor.cmake`
   用 `find_path`/`find_library` 探测；本包在 `generate()` 经 CMakeToolchain
   预置 `MEMTAILOR_INCLUDE_DIR` / `MEMTAILOR_LIBRARIES` 指向
   `memtailor/1.4` 包目录，`find_package(Memtailor REQUIRED)` 直接命中。
3. **测试依赖走 Conan 而非上游联网通道**：上游 `find_package(GTest)` 失败时
   会退回 `FetchContent` 在 configure 期 git clone googletest v1.16.0，
   CI worker 不可联网。本包用 `test_requires("gtest/1.17.0.1")` 让
   `find_package(GTest)` 直接命中；但上游判空变量 `GTEST_FOUND` 与 CONFIG
   模式实际设置的 `GTest_FOUND` 不同名，仍需 patch 0002 改写判断条件。
4. **ctest 必须在 build 根目录能跑起来**：上游把 `include(CTest)` 写在
   `src/CMakeLists.txt` 子目录里，`enable_testing()` 只对 `build/src/` 生效，
   在 build 根目录跑 `ctest` 会得到 `No tests were found!!!` 且退出码为 0。
   本包把 `include(CTest)` 提到顶层，并在 `build()` 里解析 `ctest -N`
   注册数与 `LastTest.log` 逐行结果，而不只看退出码。
5. **静态库与伞头文件都要装出去**：上游 `install(TARGETS mathic LIBRARY ...)`
   只声明 LIBRARY，静态库（ARCHIVE）漏装；`src/mathic.h` 只挂
   `PUBLIC_HEADER` 属性而无对应 DESTINATION，同样漏装。patch 0001 一并补齐。
6. **消费者链接**：`-lmathic -lmemtailor -pthread`
  （`HashTable.h`/`PairQueue.h` 直接 `#include <memtailor.h>`）。

## 依赖关系

- 编译依赖：`memtailor/1.4`（requires，运行时）
- 测试依赖：`gtest/1.17.0.1`（test_requires，仅测试期）
- 运行依赖：`memtailor/1.4`（静态链接传递）

## 打包产物

```
include/mathic.h
include/mathic/*.h
lib/libmathic.a
licenses/{lgpl-2.0.txt,lgpl-2.1.txt,lgpl-3.0.txt,README.md}
res/hmbs_upstream.json（上游 ctest 证据，供 test_package cache-hit 复发）
```

## 参考链接

- 上游仓库：https://github.com/Macaulay2/mathic
- 原始仓库：https://github.com/broune/mathic
- 本仓库版本笔记：`1.4/notes.md`
- 同生态参考：`archives/m/memtailor/1.4/notes.md`
