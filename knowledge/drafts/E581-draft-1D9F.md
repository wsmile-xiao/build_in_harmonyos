# E581 — LLVM 家族源码构建 OHOS 路线：真机原生（不设 CMAKE_SYSTEM_NAME）使 llvm-tblgen 当轮原生编+跑

## 问题概述

LLVM 家族（clang / clang-format / clangd / clang-NN-ccache / llvm 系工具）从源码构建时，
构建期必须运行 **llvm-tblgen** 等自产 host 工具生成 `.inc` 文件（指令表、内建函数表等）。
按常规"交叉编译"思路设置 `CMAKE_SYSTEM_NAME`（OHOS）会立即进入一个死结：
host 工具需要为目标平台之外的架构构建/运行，而构建期又要执行它。

OHOS PC 设备本身即 `aarch64` + `uname -s=HarmonyOS`，因此**不设 `CMAKE_SYSTEM_NAME`**、
直接走真机原生编译是可行路线：`llvm-tblgen` 与目标产物同架构，当轮编出来即可当轮运行。
本仓 `clang/20.1.8`、`clang-format-11/11.1.0` 两个包均按此路线实测通过。

## 典型错误（若走交叉路线会遇到的失败面）

> 说明：下述为交叉路线的**风险面**（本仓未实测复现），列此供识别；
> 本条目的主证据是**原生路线实测通过**（见"验证"节）。

- `llvm-tblgen: cannot execute binary file` / `Exec format error`（host 工具架构不匹配）
- 交叉工具链下 tablegen 目标被跳过或指向不存在的可执行文件
- 构建期进程无法运行刚编出的 host 工具 → 后续 `.inc` 缺失，编译成片失败

## 触发条件

- 构建系统: CMake（LLVM 官方构建体系），Ninja
- 阶段: configuration + compilation
- 目标: 从源码构建 LLVM 家族任一工具（`LLVM_ENABLE_PROJECTS=clang` 等）

## 根因分析

1. **LLVM 自举特性**：`llvm-tblgen` 由被构建的源码树自身产出，并在同一次构建中被调用；
   这要求"构建期可执行"与"目标架构"一致，天然排斥不经两阶段设计的交叉编译。
2. **设备即目标**：OHOS PC 为 aarch64，原生编译产出的 `llvm-tblgen` 可直接运行，
   故无需两阶段（host tblgen + 目标构建）。
3. **配套平台适配**（同族问题，各有独立条目，此处仅为完整路线的一部分）：
   - `llvm/cmake/config.guess` 被 `config-ix.cmake` 无条件调用，设备 `uname -s=HarmonyOS`
     不被 2011 年份的 config.guess 识别 → 覆盖为 stub 输出 `aarch64-unknown-linux-ohos`（参见 E007 家族）；
   - cmake 无 `Platform/HarmonyOS` 模块 → 提供 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`）
     挂到 `CMAKE_MODULE_PATH`，保证 `UNIX` 等平台变量正确（参见 E383）；
   - 老版本 LLVM（如 11）的 `cmake_minimum_required` 过旧，cmake 4.x 直接报
     "Compatibility with CMake < 3.5 has been removed" → `CMAKE_POLICY_VERSION_MINIMUM=3.5`（参见 E321）。

## 解决方案

### 推荐方案：真机原生源码构建（不设 CMAKE_SYSTEM_NAME）

1. `build()` 内覆盖 `llvm/cmake/config.guess` 为 stub：`#!/bin/sh` + `echo aarch64-unknown-linux-ohos`；
2. 生成 `Platform/HarmonyOS.cmake`（内容 `include(Platform/Linux)`）并挂 `CMAKE_MODULE_PATH`；
3. cmake 4.x 下注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`；
4. **只构建所需 target**（控制耗时）：如 `clang-format` + 测试基础设施 `FileCheck FormatTests count not llvm-config`；
5. 编译器/标志从 profile 取（`tools.build:compiler_executables`），不在 `self.run()` 里裸用 shell 变量（R33）。

```bash
cmake -S llvm -B build-ohos -G Ninja \
  -DCMAKE_MODULE_PATH=$PWD/_cmake_modules \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLVM_TARGETS_TO_BUILD=AArch64 \
  -DLLVM_ENABLE_PROJECTS=clang \
  -DLLVM_INCLUDE_TESTS=ON \
  -DLLVM_ENABLE_TERMINFO=OFF -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_LIBXML2=OFF
cmake --build build-ohos --target clang-format -j 4
```

### 备选方案（未实测）

交叉构建 + 两阶段：先用 host 工具链构建 `llvm-tblgen`，再以 `-DLLVM_TABLEGEN=<外部可执行文件>`
指向它完成目标构建。本仓尚未实测，采用前需真机验证。

### 禁止做法

- ❌ 对 LLVM 家族盲目设 `CMAKE_SYSTEM_NAME=OHOS` 触发交叉（会导致构建期 host 工具不可执行的死结，
  除非同时按两阶段方案准备外部 tblgen）。
- ❌ 用 stub/空实现替换 tablegen 产物（会产出功能残缺的二进制，属欺骗性适配）。

## 验证

实测记录（clang-format 11.1.0，llvm-project 11.1.0 官方源码 84,065,492 字节）：

```bash
# 全量构建 1377 个目标后
$ build-ohos/bin/clang-format --version
clang-format version 11.1.0
$ printf 'int  main( ){return 0;}' | build-ohos/bin/clang-format -style=LLVM
int main() { return 0; }
# 上游测试（同为构建期产物，证明构建链路完整）
$ build-ohos/tools/clang/unittests/Format/FormatTests   # 760/760 passed
$ build-ohos/bin/llvm-lit -sv clang/test/Format          # Passed: 21
```

同族先例：`archives/c/clang/20.1.8`（clang 20.1.8 同路线）、`archives/c/clang-format-11/11.1.0`。

## 关联条目

- 相关: E007（config.guess 不识别 HarmonyOS）、E383（Platform/HarmonyOS.cmake 缺失）、E321（cmake 4 policy）
- 对照: E286（OHOS **SDK** LLVM 15 缺 tblgen/lit 组件——那是"用 SDK 工具链"时的缺口，与本条"从源码自建工具链"互为正反面）
