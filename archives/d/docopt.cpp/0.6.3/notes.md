# docopt.cpp 0.6.3 适配笔记

## 编译环境

- 构建系统: CMake
- 编译日期: 2026-07-14
- 编译器: clang/clang++ 15.0.4
- 目标: OHOS 6.0 armv8，libc++
- 外部依赖: 无

## 编译步骤

探索构建启用 `WITH_TESTS` 与 `WITH_EXAMPLE`，以 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4。最终配方使用 Conan `CMakeToolchain`，由 `conan create` 完成源码获取、构建、安装和消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 拒绝 `cmake_minimum_required(VERSION 3.1)` | CMake 4 移除了低于 3.5 的兼容模式 | 按知识条目 E187 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | `ctest -N` 显示 0 个测试，且上游 runner 使用 Python 2 | 上游未调用 `enable_testing()`，Python 2 语法无法直接由 OHOS Python 3 运行 | 补丁将 `run_tests.py` 迁移至 Python 3；配方执行完整 175 条上游语料、官方示例，并由 test_package 验证消费者 API |
| 3 | 构建目录程序找不到 `libdocopt.so` | OHOS 构建树没有自动运行时搜索路径 | 探索/上游示例测试显式使用构建目录的 `LD_LIBRARY_PATH`；消费者测试使用 Conan `conanrun` 环境 |
| 4 | v0.6.3 安装元数据报告 0.6.2 | 上游标签中的 CMake project 版本未更新 | 补丁将 `project(... VERSION 0.6.2)` 修正为 `0.6.3` |
| 5 | pkg-config 消费 `<docopt/docopt.h>` 失败 | Conan include 元数据错误指向 `include/docopt` | 将 `cpp_info.includedirs` 修正为包的 `include` 根目录，并以标准包含路径执行消费者测试 |
| 6 | 消费者 `DT_NEEDED` 嵌入 Conan 缓存绝对路径 | HarmonyOS CMake 未为共享库写入 SONAME，且未知平台不生成版本化软链接 | OHOS/HarmonyOS 构建时显式写入与实际产物一致的 `libdocopt.so` SONAME |

## 源码修改

`0001-CMakeLists.txt.patch` 修正上游发布版本元数据，使 CMake version 文件、pkg-config 和 SONAME 与 0.6.3 标签一致。

## 验证内容

- 构建并安装共享库、静态库、头文件、上游 CMake config 和 `docopt.pc`。
- 执行官方 `naval_fate` 示例，解析命令、位置参数和 `--speed`。
- 通过 Python 3 迁移后的上游 `run_tests.py` 执行 `testcases.docopt` 的全部 175 条解析语料。
- Conan 消费者通过 `find_package(docopt CONFIG REQUIRED)` 和 `docopt::docopt` 链接。
- 消费者调用 `docopt::docopt_parse`，断言命令、两个位置参数、布尔选项和值选项。

## 消费信息

Conan CMakeDeps 暴露 `docopt::docopt`；pkg-config 名为 `docopt`；include 根目录为 `include`，消费者使用 `<docopt/docopt.h>`；链接库名为 `docopt`。
---

**编译结束**: 2026-07-14 19:25
**最终状态**: built
