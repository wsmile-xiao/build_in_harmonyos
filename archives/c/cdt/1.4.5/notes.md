# cdt 1.4.5 适配笔记

## 编译环境
- 构建系统: cmake（上游为 monorepo，实际 CMake 工程位于源码树嵌套的 CDT/ 子目录）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4 / clang++（OHOS aarch64, libc++, C++17）
- 状态: built

## 编译步骤

```bash
# 源码下载与核验（官方 GitHub tag 1.4.5）
# sha256: 5b964a00147d17f5d6ffd9c800d4f12f1e540ce8e932655469f65aea9a3005d7

# 本地构建验证（默认 + 启用测试两路径均 RC=0）
conan create archives/c/cdt/1.4.5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
conan create archives/c/cdt/1.4.5 -o cdt/*:enable_testing=True -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 报 settings.os.version 未定义 | 相对路径 profile 未加载 os.version | 使用 conan 家目录命名 profile `ohos-aarch64`（含 os.version=6.0） |
| 2 | conan source() 下载 GitHub 超时（python urllib 直连不通，curl 可通） | 环境网络对 python urllib 与 curl 表现不同 | 将已验证 tarball 预置到 `~/.conan2/download_cache/s/<sha256>`（download_cache 按 sha256 键，命中即跳过网络） |
| 3 | CMake 报 source directory 无 CMakeLists.txt | 上游为 monorepo：实际工程在 tarball 嵌套的 `CDT/` 子目录（get() strip_root 只剥一层） | conanfile source() 中将 `CDT/` 内容上移至 source 根，与 .work 双轨结构/补丁路径同口径 |
| 4 | 测试编译失败：找不到 `catch2/benchmark/catch_benchmark.hpp` 等 v3 多头头 | 制品仓已发布 catch2/2.13.10-r0 为 v2.13 合并头（仅 catch.hpp + 4 reporter 头），上游测试按 v3 多头 include 编写 | 补丁 0002：5 条 include 合并为 `#define CATCH_CONFIG_ENABLE_BENCHMARKING` + `#include <catch2/catch.hpp>`（v2.13 合并头含全部所需宏） |
| 5 | CMake `find_package(Catch2 3)` 失败下落空 submodule 分支 | 已发布 catch2 版本 2.13.10 不满足 ≥3；tests/Catch2 子模块在 tarball 中为空 | 补丁 0001：放宽为 `find_package(Catch2 QUIET)` |
| 6 | `Catch2::Catch2WithMain` 目标找不到、`include(Catch)`/`catch_discover_tests` 不可用 | 已发布 catch2 配方仅声明 `Catch2::Catch2`，且不透出 extras/Catch.cmake | 补丁 0001：改链 `Catch2::Catch2` + `CATCH_CONFIG_MAIN` 生成 main；catch_discover_tests 改单 add_test（WORKING_DIRECTORY=tests/） |
| 7 | conandata patches 未应用（configure 仍走旧分支） | conandata.yml 的 patches 需按版本号组织为 dict 列表（`patches: {version: [entry]}`），直接按文件名组织的 dict 不被识别 | 修正为版本键列表格式 |
| 8 | 上游配方无条件 require catch2/3.4.0（未发布） | 上游 conanfile 将 catch2 写成无条件依赖（测试才需要） | 适配为 `enable_testing=True` 时才 require catch2/2.13.10-r0（已发布），默认无依赖 |
| 9 | 鸿蒙专项测试断言失败（vertices=12/fixedEdges=4） | CDT 确定性行为：三角网含 3 个超三角形顶点（9+3=12）；两条相交约束对角线经 TryResolve 交点分裂为 4 段 | 断言按实际语义修正（擦除超三角形后顶点回到 9） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：测试注册段适配已发布 catch2（find_package 放宽、Catch2::Catch2 + CATCH_CONFIG_MAIN、单 add_test）
- `patches/0002-tests-cdt.test.cpp.patch`：5 条 catch2 v3 多头 include 合并为 v2.13 合并头 catch.hpp（+CATCH_CONFIG_ENABLE_BENCHMARKING）

## 依赖版本

- catch2/2.13.10-r0（制品仓已发布；仅 enable_testing=True 时依赖，库本体无依赖）

## 验证结果

- 上游测试：28/28 通过（4788 断言，0 失败）；`source_declared_total=25`（18×TEST_CASE + 7×TEMPLATE_LIST_TEST_CASE），类型实例化后 32，当前配置注册 28（2 Callbacks 互斥守卫未实例化 + 2 Benchmarks 隐藏基准不计独立用例），全量口径 28/30=93.3%，可执行集合 28/28=100%
- standards_check：编译+运行 RC=0
- 消费者验证（test_package）：test_cdt → "triangulation OK (2 triangles, 4 vertices)" RC=0
- 鸿蒙专项测试（ohos_specific_test）：int64 索引类型 + 多批次插入 + 显式断言 → PASSED（9 vertices, 4 constraint edges, 8 triangles）RC=0
- W3 本地 CI：`.ci-result.json` exit_code=0（log_sha256=5c00ad4f…）
- W2 PR 原子性：仅含 cdt 配方变更，无框架文件

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | OHOS 适配配方（MPL-2.0, header-only） |
| test_package/ | 消费者验证 + 鸿蒙专项测试（含 MANIFEST.yml） |
| patches/ | 2 个测试适配补丁 |
| reports/test-report.md | 测试报告（双口径台账摘要） |
| reports/knowledge-candidate-ledger.md | 知识候选台账与四范围查重 |
| knowledge/drafts/DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation.{kv,md} | 知识库扩展草稿（路径 B） |

## 注意事项

- 上游 catch2/3.4.0 未发布，测试适配使用已发布的 2.13.10-r0 合并头；未来 catch2 v3 发布后可用其多头布局并撤销补丁 0001/0002
- CDT 默认 header-only（INTERFACE target）；`CDT_USE_AS_COMPILED_LIBRARY=ON` 可产 libCDT(a)（本任务未启用）
