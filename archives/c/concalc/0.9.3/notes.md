# concalc 0.9.3 适配笔记（HarmonyOS PC · CMake）

## 定位
- 产出 CLI 工具 bin/concalc（Extcalc 计算器的控制台版本，C++，GPL-2.0-or-later）。

## 源
- 上游托管于 SourceForge extcalc-linux 项目（concalc 的官方分发处）。
- https://downloads.sourceforge.net/project/extcalc-linux/extcalc-linux/0.9.3/concalc-0.9.3.tar.gz
- sha256: 464e8cafcda7f19f3c80bce60d5c355d3622770cd85d893419498eec2b098edb

## W0/W0b
- preflight_check.sh：无依赖声明，通过。
- 本仓库无同软件历史归档。
- lang-preflight：task=cpp，detected=cpp（C++ 主体 concalc.cpp/global.cpp），通过。

## 构建要点
- CMakeLists 声明 CMAKE_MINIMUM_REQUIRED(VERSION 2.4.3)；设备 cmake 4.1.2 已移除
  <3.5 兼容（直接 configure 报错）。配方 generate() 用 CMakeToolchain 注入
  CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 官方迁移变量），无需修改上游源码。
- 探索构建：140 条 -Wnull-dereference 告警（src/list.h 的 `*((T*)NULL)` 惯用法），
  非错误且执行路径不触发，保持上游代码不动。
- 安装：cmake.install()（bin/concalc + man 页），package() 补装 COPYING/README 到 licenses/。

## 行为向量（真机实测，test_package 断言依据）
- `-v` → `Version: 0.9.3 2010-04-04`
- `concalc "2*(3+7/2)"` → `13`
- `concalc "1/3"` → `0.333333333333333333333333333333333`（34 位精度）
- `concalc "sqrt(2)"` → `1.4142135623730950488016887242097`

## 上游测试账本（R51）
- 上游无测试：CMakeLists 无 ENABLE_TESTING/add_test，源码树无测试源码/脚本。
  N_static = 0，N_executed = 0（如实申报）。
- 消费者测试（test_package）4 用例 / 4 断言：驱动真实 concalc 二进制做版本横幅
  与三类表达式求值断言。

## 状态
built —— conan create 真机验证通过后回填（见 .ci-result.json / reports/）。
---

**编译结束**: 2026-09-09 00:11
**最终状态**: built
