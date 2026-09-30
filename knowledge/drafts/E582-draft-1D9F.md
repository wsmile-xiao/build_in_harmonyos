# E582 — llvm-lit 上游测试套件在源码构建下的两个隐式执行前提

## 问题概述

从源码构建 LLVM 家族并执行其上游 lit 测试套件时，有两个**不在错误信息里明说**的前提：
①构建目录必须位于源码树内；②lit 依赖的测试工具目标必须一并构建。
两者任一缺失，表现为"lit 直接 fatal 退出"或"套件找不到"，容易被误判为"上游测试无法运行，
只能跳过"——而实际是可以跑通的（实测 21/21 通过）。

## 错误特征

```
fatal: Did not find count in /path/build-ohos/bin
llvm-lit: error: unable to find test suite / cannot find suite 'clang'
```

## 触发条件

- 构建系统: CMake + Ninja（源码构建 LLVM，非 SDK 工具链）
- 阶段: testing（`llvm-lit` / `bin/llvm-lit -sv <suite>`）
- 典型包: clang-format 11.1.0（本仓 `archives/c/clang-format-11/11.1.0`）

## 根因分析

1. **构建目录必须在源码树内**：llvm-lit 的 `map_config` 以构建目录为基准解析套件与源码目录
   （形如 `bdir/../<子项目>`，如 `build-ohos/../clang`）。若把构建目录放在源码树之外
   （如 conan 默认的独立 build 目录或 `/tmp` 下的临时目录），`bdir/../clang` 指向不存在的位置，
   套件无法定位 → lit 报找不到套件。
2. **测试工具目标必须一并构建**：lit 的 RUN 行大量使用 `count` / `not` / `FileCheck` /
   `llvm-config` 等工具，它们不是默认构建目标的一部分；只构建 `clang-format` 时
   `bin/` 下没有这些工具，lit 第一步就 `fatal: Did not find count in .../bin` 整体退出，
   给人的错觉是"lit 套件不可用"。

## 解决方案

### 推荐方案：构建目录置于源码树内 + 目标列表补测试工具

```bash
# 1) 构建目录放在源码树内（conan 配方中即 source_folder/build-ohos）
cmake -S llvm -B "$SRC/build-ohos" -G Ninja ...

# 2) 目标列表包含 lit 所需的测试工具与单测目标
cmake --build "$SRC/build-ohos" --target \
      clang-format FileCheck FormatTests count not llvm-config -j 4

# 3) 运行单测与 lit 套件
"$SRC/build-ohos/tools/clang/unittests/Format/FormatTests"      # 760/760 passed
cd "$SRC/build-ohos" && bin/llvm-lit -sv "$SRC/clang/test/Format"   # Passed: 21
```

### 备选方案

构建目录无法置于源码树内时，参考 E387 的"自包含替换式 lit.cfg.py"（注入 site 属性）
独立运行 lit 套件。

### 禁止做法

- ❌ 因 lit 启动失败就删减/跳过上游测试并宣称"上游无测试"（R51 要求真实清点与实跑）。
- ❌ 修改上游 lit 配置或测试文件以绕过工具缺失。

## 验证

```bash
ls build-ohos/bin/llvm-lit build-ohos/bin/FileCheck build-ohos/bin/count build-ohos/bin/not build-ohos/bin/llvm-config
cd build-ohos && bin/llvm-lit -sv ../clang/test/Format
```

实测（clang-format 11.1.0）：修正前 lit 首行即 `fatal: Did not find count ...`；
修正后 `Passed: 21`，与单测 `FormatTests` 760/760 共同构成 781/781（100%）的上游测试证据。

## 关联条目

- 相关: E387（lit 框架在 OHOS 的最小可运行集与自包含 site 配置）、E286（SDK LLVM 15 缺 lit/FileCheck —— 注意区分：本条是"源码自建时目标没勾"，E286 是"SDK 根本没有"）
- 相关: E581（同源码构建路线的构建策略）
