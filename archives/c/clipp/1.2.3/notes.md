# clipp 1.2.3 适配笔记

## 编译环境
- 构建系统: custom（header-only 单头文件，无 CMake/Make 构建入口）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

clipp 是单头文件库（include/clipp.h），无独立构建系统：

1. 获取官方源码：https://github.com/muellan/clipp/archive/refs/tags/v1.2.3.tar.gz
   sha256=73da8e3d354fececdea99f7deb79d0343647349563ace3eafb7f4cca6e86e90b
2. conan 配方为 header-library：仅打包 include/clipp.h + LICENSE
3. 上游测试逐个编译运行：
   ```
   clang++ -I include -std=c++11 -Wall -Wextra -Wpedantic -O0 -o <bin> test/<t>.cpp
   ```
   39 个独立测试可执行，38 通过 / 1 失败
4. test_package 消费者测试（clipp::parse 解析 argv）+ HarmonyOS 专项测试

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | values_conversion_test 第 165 行失败（char "-128" → -128 用例） | OHOS aarch64 (AAPCS64) 默认 char 为无符号（0..255），上游测试假定有符号 char 语义；clipp make<char> 用 strtoll+clamp，无符号 char 下 -128 clamp 为 0 | 属平台 ABI 语义差异，非 clipp 缺陷；未修改上游测试；38/39=97.4% 通过率如实上报，鸿蒙特有测试显式校验 char 符号性 |

## 源码修改

无（header-only，未改上游源码；无补丁）

## 测试统计

- 源码声明测试可执行：39（test/*.cpp，每个为独立 main 可执行）
- 配置实例化/运行：39
- 通过：38 | 失败：1（平台 ABI 语义差异）| 未运行：0
- 通过率：38/39 = 97.4%

## 知识沉淀

OHOS aarch64 默认无符号 char：上游测试假定有符号 char 语义时可能失败（如 clipp values_conversion_test 的 -128 用例）。诊断：先验证 char 符号性（volatile char c=-1; c>=0），再区分平台 ABI 边界与库缺陷。
---

**编译结束**: 2026-09-05 04:33
**最终状态**: built
