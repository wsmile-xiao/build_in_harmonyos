# Makefile 系 C 库在 OHOS 首编：uname -s 平台检测不匹配 + 硬编码 gcc

> 草稿 ID: `DRAFT-ffc.h-26.07.01-makefile-uname-gcc-hardcode`（配对 `.kv` 同 stem）
> 来源: ffc.h 26.07.01 第一轮适配（executor pc1-28, 2026-09-22）
> 路径判定: 知识库扩展（Path B, new_draft）——C1+C2 合并条目

## 问题

在 HarmonyOS PC（OHOS, arm64）首次编译以 **Makefile 为主构建** 的 C 库时，出现两类首错：

1. **平台特性宏缺失**
   ```text
   test_src/sonicsv.h:1611:36: error: use of undeclared identifier 'MADV_SEQUENTIAL'
   test_src/sonicsv.h:1611:54: error: use of undeclared identifier 'MADV_WILLNEED'
   ```
   根因：Makefile 用 `UNAME_S := $(shell uname -s)` + `ifeq ($(UNAME_S),Linux)` 决定是否加
   `-D_DEFAULT_SOURCE`；OHOS 上 `uname -s` 返回 `HarmonyOS`（不是 `Linux`），条件不成立，
   依赖特性宏的 POSIX 声明（`madvise` / `MADV_*`）未声明。

2. **硬编码 gcc 无编译器**
   ```text
   make: gcc: No such file or directory
   make: *** [Makefile:30: out/test_runner] Error 127
   ```
   根因：上游 Makefile 直接调用 `gcc`（如 `gcc -xc ... -fsyntax-only`），而 OHOS PC 环境
   只提供 clang 15（无 gcc / cc / c++）。

## 根因

两个独立根因叠加，均为上游构建脚本的"平台假设"在 OHOS 不成立：

- Makefile 的 `uname -s` 平台分支：Linux 假设（`uname -s` = `Linux`）在 OHOS 返回 `HarmonyOS` 时不匹配，特性宏 `-D_DEFAULT_SOURCE` / `-D_POSIX_C_SOURCE` 缺失。
- Makefile 的编译器硬编码：`gcc` 命令直接写在 Makefile 目标里，而 OHOS 工具链只安装 clang。

## 方案

1. **特性宏显式恢复**：编译命令显式传
   `-D_DEFAULT_SOURCE -D_POSIX_C_SOURCE=200809L`
   —— 与上游 CMakeLists.txt 的 `target_compile_definitions(... _POSIX_C_SOURCE=200809L _DEFAULT_SOURCE)`
   声明保持一致（优先取上游已声明的宏组合，而非自造）。
2. **编译器垫片**：Makefile 硬编码 gcc 且不便改源码时，本地建 gcc→clang、c++→clang++ 符号链接
   并前置到 PATH（不修改上游源码、不生成补丁）：
   ```bash
   mkdir -p ~/tmp/ohc-shims && ln -sf $(which clang) ~/tmp/ohc-shims/gcc \
     && ln -sf $(which clang++) ~/tmp/ohc-shims/c++ \
     && PATH=~/tmp/ohc-shims:$PATH make test
   ```
3. 可选：上游同时提供 CMakeLists.txt 时优先走 CMake 配置编译（其宏声明通常已正确），
   Makefile 仅用于复跑测试入口。

## 验证（ffc.h 26.07.01）

- 加宏 + 垫片后：`test_runner` / `test_int_runner` / `test_runner_src` / `test_int_runner_src`
  / `supplemental_tests` / `supplemental_tests_src` / `test_exhaustive_runner`（受限采样）
  / `example` 全部编译并运行 PASS。
- Conan 配方（header-only）`conan-verify` G0-G4 全 PASS；test_package 消费者测试真实调用
  `ffc_parse_double_simple` / `ffc_parse_i64_simple`，ALL OK。

## 适用边界 / 反例

- ✅ 适用：Makefile 主构建 + `uname -s` 平台分支 + 硬编码 gcc/g++ 的 C/C++ 库。
- ❌ 反例（走既有条目，勿套用本方案）：
  - autotools 库 → `E007` / `E160`（config.guess 打 HarmonyOS 补丁）；
  - CMake `CMAKE_SYSTEM_NAME` 平台块不匹配 → `E140`；
  - configure 探测 `checking for program gcc... no` → `E359`（HOSTCC/CC_FOR_BUILD 映射）。
- 📌 关联：stb-style 单头实现库（如 ffc.h 的 `FFC_IMPL`）消费者 TU 需定义实现宏才能链接
  实现，见 `DRAFT-enet-2.7.0-single-header-impl-lib` 模式（本库实证：test_package 在
  `#include <ffc.h>` 前 `#define FFC_IMPL`）。

## 查重差异（七轴）

| 轴 | 结论 |
|----|------|
| exact_duplicate | false |
| causal_duplicate | false（与 E140/E160/E007 根因同源但构建系统口径不同） |
| trigger_overlap | E140（CMake 平台块）、E359（configure 探测 gcc）部分重叠 |
| solution_overlap | 无方案级重复 |
| combination_novelty | true |
| boundary_novelty | true |
| test_migration_novelty | 部分 |

## 关系

- similar_to: E140, E359, E007, E160
- caused_by: `uname -s` 在 OHOS 返回非 Linux；OHOS 无 gcc
- prerequisite_of: （无）
- conflicts_with: （无）

## 关联文件

- 配方: `archives/f/ffc.h/26.07.01/conanfile.py`
- 笔记/台账: `archives/f/ffc.h/26.07.01/notes.md`
