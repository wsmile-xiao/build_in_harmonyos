# cpp-lazy 9.0.1 HarmonyOS PC 适配笔记

## 官方来源核验

- 官方仓库：https://github.com/Kaaserne/cpp-lazy
- 官方标签：`v9.0.1`
- 标签 commit：`99715931445a8ed0ef16cf26bb97dbfe53cae8a4`
- 官方源码：https://github.com/Kaaserne/cpp-lazy/archive/refs/tags/v9.0.1.tar.gz
- SHA-256：`16cbaf58002ed46d369e8b87df4ac4b1fc47265fdffed0c5009b3ff8c7f013db`
- 许可证：MIT（`LICENSE.md`）

采用完整官方标签归档而非仅含发布文件的 `cpp-lazy-src.zip`，因为赛事要求清点并运行
完整上游测试，后者不包含 `tests/` 与 `examples/`。

## 库与构建特性

- header-only CMake `INTERFACE` 库，支持 C++11/14/17/20；本次验证使用 C++17。
- 默认启用 fmt 格式化接口；Conan 公共依赖为仓库远端可用的 `fmt/12.2.0`，并固定
  `shared=True`，确保干净的 OHOS Worker 直接下载已发布的共享库二进制，不回退到
  GitHub 源码构建未发布的静态变体。
- 上游正式测试使用 doctest，由 47 个 `.cpp` 文件构建为一个 `tests` 可执行文件并注册为一个 CTest；源码静态清点共 291 个 `TEST_CASE` 声明。
- 安装内容为 `include/Lz/`、CMake package config、pkg-config 文件和许可证，无静态库、共享库或命令行程序。

## 适配内容

1. `0001-CMakeLists.txt.patch`：官方 `v9.0.1` 标签中的 `project(VERSION)` 仍为
   `9.0.0`，改为 `9.0.1`，确保 `find_package(cpp-lazy 9.0.1)` 正确匹配。
2. `0002-cmake-cpp-lazyConfig.cmake.in.patch`：把构建时选择的 standalone/fmt
   模式写入安装后的配置，避免消费方因未定义配置变量而错误寻找 bundled fmt。
3. `0003-tests-CMakeLists.txt.patch`：只把 doctest 的 FetchContent 获取方式替换为
   `find_package(doctest CONFIG REQUIRED)`；不改测试源码、用例、断言或预期结果。
4. OHOS Clang 15 对上游测试的 `-Wno-unsafe-buffer-usage` 尚不识别，SDK 驱动还会
   对注入的 `--gcc-toolchain` 产生未使用诊断；配方仅关闭这两类诊断，其余上游
   `-Weverything -Werror` 规则保持启用。

## 依赖

- 公共依赖：`fmt/12.2.0`（`shared=True`，上游默认格式化功能）。
- 测试依赖：`doctest/2.4.11`（与上游指定的 2.4.12 同属 2.4 系列；仅用于完整上游测试）。
- 两个依赖均通过赛事 Conan 远端配方解析，不下载或内置第二份依赖源码。

## 上游测试普查与结果

- 正式测试目录：`tests/`
- 测试源文件：47
- CTest 测试目标：1（`tests`）
- doctest 源码 `TEST_CASE` 声明：291
- doctest 运行时适用测试用例：290
- doctest 运行时断言：12,348
- 结果：290/290 用例、12,348/12,348 断言通过，0 失败、0 跳过。
- 291 个源码声明与 290 个运行用例的差额为 `tests/string_view.cpp` 中的 1 个回退实现测试；上游使用 `#if !defined(LZ_HAS_STRING_VIEW)` 守卫，C++17 提供 `std::string_view` 时按设计不注册该项，非修改、失败或跳过。
- 上游示例：`examples/CMakeLists.txt` 列出的 48 个示例目标全部编译通过。
- 赛事静态清点总数：339（291 个 doctest 声明 + 48 个示例目标）；适用项 338/338 全部通过。

## 消费者验证

`test_package` 只使用 Conan 打包后的 `cpp-lazy::cpp-lazy` 目标，覆盖 map、filter、
管道组合、to、range、accumulate、contains、zip 和 fmt 格式化，共 12 项运行时检查；
12/12 全部通过。

## 验证结论

- HarmonyOS/OHOS AArch64 Clang 15 CMake 配置、完整上游构建和安装：通过。
- 上游 doctest：290/290 用例、12,348/12,348 断言通过。
- Conan `test_package`：1/1 程序、12/12 检查通过。
- CMake 版本化包发现、目标链接、pkg-config 元数据和产物边界检查：通过。
- 仓库门禁、知识检查、图谱验证及全部仓库回归测试：通过。
---

**编译结束**: 2026-09-10 07:17
**最终状态**: built
