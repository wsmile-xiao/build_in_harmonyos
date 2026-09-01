# nameof 0.10.6 — OHOS 适配笔记

## 结论
- header-only C++17，零运行时依赖，单头文件 `include/nameof.hpp`。
- package_type=header-library + `package_id().info.clear()`（参照仓库先例
  `adamstark-audiofile/1.1.4`）。
- 源码在 OHOS/aarch64 无需任何补丁（patches: []）。

## 上游测试真实执行
- 上游自带两个 doctest 套件：`test/test.cpp` + `test/test_aliases.cpp`，
  各自 `#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN`，共 95 TEST_CASE + 49 SUBCASE。
- doctest.h 已 vendor 于 `test/3rdparty/doctest/`，**无需联网**。
- 上游 `test/CMakeLists.txt` 强制 `-Wall -Wextra -pedantic-errors -Werror`，
  OHOS clang 会把它打成硬错误，因此 build() 改为直接用 `clang++ -std=c++17`
  编译这两个文件并运行（不改上游源码，仅去掉 -Werror）。
- `fmt` 可选：test.cpp 用 `__has_include(<fmt/format.h>)` 守卫相关 SUBCASE，
  无 fmt 也能全过。

## 与同类先例的关系
- 结构照抄 `archives/a/adamstark-audiofile/1.1.4`（header-library + package_id
  clear + can_run 守卫），测试执行方式照抄 `archives/t/tommyds/3.0`（build() 里
  真实运行上游自测）。

## 版本对齐（§六b）
- 任务 #5179 = conan 0.10.6 = 分支 feat/nameof-0.10.6 = 目录 archives/n/nameof/0.10.6。
---

**编译结束**: 2026-08-31 00:24
**最终状态**: built
