# fast_float 6.1.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (aarch64-linux-ohos, clang 15.0.4)
- 状态: built（待 finish W3 后定稿）

## 编译步骤

fast_float 为 header-only 库，无第三方依赖（W0 依赖预检通过）。

1. 官方源码：https://github.com/fastfloat/fast_float/archive/refs/tags/v6.1.6.tar.gz
   - sha256=4458aae4b0eb55717968edda42987cabf5f7fc737aee8fede87a70035dba9ab0
   - 版本经 CMakeLists `project(fast_float VERSION 6.1.6)` 核验。
   - 本机 GitHub 直连超时，用 ghfast.top 镜像拉取官方包与本地缓存比对 sha256 完全一致。
2. Conan 配方：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同`。
   - CMakeToolchain OHOS 分支设 CMAKE_SYSTEM_NAME=Linux（R32）。
   - FASTFLOAT_TEST=OFF：上游 tests/CMakeLists.txt:30 用 FetchContent_Populate(doctest)
     与 supplemental_test_files 从 github.com clone，CI worker 禁 GitHub 网络。
   - header-only，无系统同名库冲突（R26 不涉及）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 (Errno 110) | 本机/CI 网络禁 GitHub | 镜像 ghfast.top 拉官方包，sha256 比对一致；conandata.yml 仍保留官方 URL（R39） |
| 2 | 上游 tests 需 doctest 2.4.11 | tests/CMakeLists.txt FetchContent 从 GitHub clone | 镜像下载官方 doctest.h 本地编译运行；配方中 FASTFLOAT_TEST=OFF 由 test_package 覆盖 |

## 源码修改

无（header-only，零补丁）。

## 依赖版本

无外部依赖。

## 验证结果

- 上游测试（默认启用组 12 入口）：全部通过，basictest 20/20 test cases、6859/6859 assertions。
- 穷举组 7 入口：编译通过，全空间穷举单轮需数小时（硬阻塞），40s 限时探测持续进度无失败。
- HarmonyOS 专项测试（test_package/ohos_special_test.cpp）：15 checks ALL OK，
  __OHOS__ 分支实际校验字节序与硬浮点路径。
- 消费者测试（test_package/test.cpp）：解析 "3.14" == 3.14 通过。
- 台账详见 reports/upstream-tests-ledger.md。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake header-only 配方 |
| conandata.yml | 官方源 + sha256 |
| test_package/test.cpp | 消费者 API 测试 |
| test_package/ohos_special_test.cpp | HarmonyOS 专项测试 |
| test_package/MANIFEST.yml | 测试声明 |

## 注意事项

- header-library 类型，无 commands.json 需求（R38：无可执行产物）。
- 穷举测试如需全量运行，需显式 FASTFLOAT_EXHAUSTIVE=ON 并在充足预算轮次运行。

## W4 审计

- verdict=pass（P0/P1=0），详见 reports/audit-result.json。
---

**编译结束**: 2026-09-01 17:33
**最终状态**: built
