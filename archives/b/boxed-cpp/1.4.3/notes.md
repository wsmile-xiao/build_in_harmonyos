# boxed-cpp 1.4.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt 定义 INTERFACE 目标 boxed-cpp::boxed-cpp）
- 编译日期: 2026-09-07
- 编译器: OHOS clang 15.0.4 (aarch64-linux-ohos) / libc++
- 状态: built（conan-verify 全门禁通过；未跑 release/upload 流水线）
- 上游: https://github.com/contour-terminal/boxed-cpp（tag v1.4.3，官方 GitHub archive）

## 编译步骤
1. init-build 下载官方 tarball（SHA256 75afd9c1...，与 git tag v1.4.3 内容 diff 一致）
2. lang-preflight: task=cpp, detected=cpp（CMake + 源文件 100% C++）通过
3. 本地手工验证上游测试：clang++ -std=c++20 编 test-boxed-cpp.cpp + Catch2 v3.4.0 → 14/15 通过
4. conan-init 生成配方骨架 → 重写为 CMake header-only 配方
5. conan-verify 全门禁 PASS（G0-G4 + L2/L4/L5）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | boxed.hpp include 即编译失败（std::formatter 特化 4 errors） | 上游用 __has_include(<format>) 判 formatter；OHOS clang15 libc++ 的 <format> 不完整：_LIBCPP_HAS_NO_INCOMPLETE_FORMAT、formatter 为双模板形参无默认实参 | 0001 patch：条件改 __cpp_lib_format（与上游 test 文件同款守卫）。无完整 std::format 时仅失去 formatter 支持，编译可用 |
| 2 | conan create patch 应用 "hunk doesn't match" | 手工 patch @@ 行号/上下文与干净源不符（差 1 行） | 用干净解压源 diff 生成精确 hunk（@@ -207,7 +207,7 @@），dry-run 验证 |
| 3 | test_package CMakeToolchain 重复 | generators 与 generate() 同时实例化 | test_package generators 仅保留 CMakeDeps |
| 4 | test_package static_assert 失败 | constexpr 对象使 decltype 带 const | 改运行时变量 + 修正 is_same 预期 |

## 源码修改
- patches/0001-format-feature-test.patch：boxed.hpp 的 formatter 集成条件从 __has_include(<format>) 改为 __cpp_lib_format

## 依赖版本
- 无运行时依赖（header-only）。上游测试需 Catch2 v3.4.0（本仓制品仓仅 v2.13.10-r0，未入库；本地用官方 Catch2 v3.4.0 tarball 手工编译执行上游测试作证据）

## 验证结果
- 上游测试（本地，Catch2 v3.4.0）：All tests passed (21 assertions in 14 test cases)，运行 exit 0
- 静态声明 15 TEST_CASE；formatter 用例因 OHOS libc++ 无 __cpp_lib_format 被上游条件编译排除（实跑 14）
- conan-verify: G0-G4 全 PASS；conan create + test_package 真实调用 boxed API 通过

## 交付物
- archives/b/boxed-cpp/1.4.3/{conanfile.py, conandata.yml, manifest.yaml, notes.md, patches/0001-*.patch, test_package/}

## 注意事项
- 上游 search-url/registry 会把 boxed-cpp 误导向 waterlan.home.xs4all.nl（通用猜测模板假阳性，该域 2025 已关停）；真实上游是 contour-terminal/boxed-cpp
- E017 镜像注入会临时污染 conandata.yml，验证后已恢复官方 URL 并清理 .ghfast-bak
---

**编译结束**: 2026-09-07 01:42
**最终状态**: built
