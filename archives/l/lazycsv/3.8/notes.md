# lazycsv 3.8 — 适配笔记

## 结论摘要

- header-only C++17 单头文件 CSV 惰性解析库，无外部依赖，无编译产物，无 CLI（不需要 commands.json）。
- 上游 14 个独立 doctest TEST_CASE 全部通过；HarmonyOS 专项测试 + 消费者测试通过。
- conan create（ohos-aarch64 profile）通过；W2/W3 门禁通过。

## 上游版本语义（重要）

- 上游仓库 **没有 git tag**（GitHub API 与 jsdelivr data API 均返回空 tags；codeload 对
  v3.8/3.8/v3.8.0/3.8.1/v3.8.1 全部 404）。
- 根 CMakeLists.txt：`cmake_minimum_required(VERSION 3.8...3.20)` 且
  `project(lazycsv VERSION 1.2.0 ...)`。
- 任务版本 **3.8 取自 `cmake_minimum_required(VERSION 3.8...)`**；官方源固定到
  master 提交 `6c36a9d66be1e652b0c06d4e34fb053b93caf0ff`（2026-02-13）的官方
  commit 归档，SHA-256=19bc1673d9a60b82ed71f3ae8cfaa36105c15d6f6f2dfa496ca8d2386f9c573f。
- README 自述"最新版本单头文件即 include/lazycsv.hpp"，无发布流程。

## 构建要点

- CMake INTERFACE 库（`add_library(lazycsv INTERFACE)`），仅 `install(DIRECTORY include/ ... *.hpp)`。
- 配方 build 关闭 BUILD_TESTING（上游测试在适配阶段独立运行并计入双口径台账）。
- conanfile.py: package_type=header-library，cpp_info.libs=[]，package_id 清空（单二进制 id）。
- 无第三方依赖，W0 预检通过（ohpcd 无依赖可查）。

## 上游测试（14 独立用例）

- test/main.cpp（235 行）: 14 个独立 TEST_CASE，doctest 框架头 test/doctest/doctest.h 不计独立用例。
- test/CMakeLists.txt: `add_executable(main main.cpp)` + `add_test(main main)`，
  POST_BUILD 将 inputs/ 拷贝到构建目录。
- 用例覆盖：mmap_source（zero_length/non_existent/basic.csv）、字符串源解析、
  空单元格/空行/末行换行/不同列数/TAB 与空格 trim/自定义分隔符/引号单元格/CRLF 等。

## OHOS 注意事项

- mmap_source 依赖 mmap：OHOS 上对普通文件可用；/tmp 为 erofs 只读，测试输入放工作目录。
- 无平台特殊适配代码（纯头文件库）。
---

**编译结束**: 2026-09-27 04:51
**最终状态**: published
