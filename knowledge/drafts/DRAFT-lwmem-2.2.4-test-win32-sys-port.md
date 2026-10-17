# DRAFT-lwmem-2.2.4-test-win32-sys-port：上游测试套件硬编码 win32 系统端口的适配

> Contributor: pc2-48-executor | Status: Draft | Updated: 2026-09-28
> Source: lwmem 2.2.4 HarmonyOS PC 适配（lwmem-2.2.4-r01，task_id lwmem-2.2.4-r01-bootstrap-and-adapt-pc2-48-20260928T080920Z）

## 问题

lwmem 2.2.4（lightweight embedded dynamic memory manager，MIT）在 Linux / HarmonyOS PC (arm64)
上做 Conan 适配时，上游测试套件首错为：

```text
fatal error: 'windows.h' file not found
  #include "windows.h"
```

触发位置是每个测试子目录的 `tests/<name>/lwmem_opts.h`，且 `tests/CMakeLists.txt` 硬编码
`set(LWMEM_SYS_PORT "win32")`（把 `lwmem_sys_win32.c` 编入测试库目标）。

## 根因

- 库核心 `lwmem.c` / `lwmem.cpp` 本身可移植：`LWMEM_CFG_OS` 默认 0，此时
  `LWMEM_PROTECT/UNPROTECT` 宏为空实现，完全不依赖系统端口。
- 但上游测试配置把 `LWMEM_CFG_OS` 置 1、`LWMEM_CFG_OS_MUTEX_HANDLE` 绑定到 Windows
  `HANDLE`，并在 opts 头无条件 `#include "windows.h"`。
- Linux / OHOS 工具链无 `windows.h`，因此上游测试（而非库源码）不可编译。
- 属于测试基础设施的 win32 硬编码，不是库源码缺陷；库源码零改动。

## 方案（最小改动，仅测试配置头）

对 7 个测试子目录的 `lwmem_opts.h` 做等价替换：

| 字段 | 原值 | 新值 |
|---|---|---|
| `#include "windows.h"` | Windows 头 | `#include <stddef.h>` |
| `LWMEM_CFG_OS` | 1 | 0 |
| `LWMEM_CFG_OS_MUTEX_HANDLE` | `HANDLE` | `void*` |

验证结果（本机，clang 15 / cmake 4.1.2，7 个测试配置各 1 个 ctest 用例）：

| 配置 | 结果 |
|---|---|
| test_available_mem | 100% passed |
| test_memory_structure | 100% passed |
| test_region_allocation | 100% passed |
| test_region_size_alignment | 100% passed |
| test_simple_config | 100% passed |
| test_statistics | 100% passed |
| test_stats_compile | 100% passed |

## 适用边界

- 适用：核心库可移植、测试套件按 Windows 端口组织（系统端口目录含 win32 变体、
  测试 opts 硬编码 `windows.h` / `HANDLE` 句柄）的嵌入式/可移植 C/C++ 库，在
  Linux / HarmonyOS PC 上适配时上游测试默认不可编译。
- 已排除：本库仅有 cmsis_os / threadx / win32 三种系统端口，无 pthread 端口，
  因此不能走"测试 CMake 平台分支选端口"方案，只能关闭测试配置的 OS 支持。
- 不适用：库源码自身依赖 Windows API（此时需另做 POSIX 移植，非本模式）。

## 反例与限制

- 禁止"只删 windows.h 却保留 LWMEM_CFG_OS=1 + HANDLE"：HANDLE 类型会未定义，
  编译仍失败，属不完整修复。
- 关闭 OS 支持后测试在单线程下运行，线程安全路径（OS=1 时互斥量保护分配路径）
  不再被测试覆盖；如需覆盖请另行提供 pthread 系统端口。
- 测试运行依赖 `ctest` 从 tests 子构建目录执行（顶层 CTestTestfile 无测试注册，
  `ctest` 需在 `build/tests/` 内运行）。

## 查重差异（vs 既有知识条目）

- E375（Select Windows positively and unknown systems…）：针对 CMake 平台检测把未知系统
  错分到 Windows 源码选择（ProcessWin32.c/tif_win32.c），修复点是 CMake 平台判定分支；
  本模式是测试配置头硬编码 `windows.h`，修复点是测试 opts 关闭 OS 支持，不涉及
  CMake 平台选择逻辑。
- E532（CMake if(WIN32)/elseif(UNIX)/else() 平台三分支）：针对 configure 阶段平台判定
  FATAL；本模式是编译阶段测试配置头缺失 windows.h，两者错误面不同。
- 快照查重（gitcode main @ 7577cabc，knowledge 稀疏快照）：graph + drafts 均无
  LWMEM / LWMEM_SYS_PORT / 测试 opts windows.h 等价条目。