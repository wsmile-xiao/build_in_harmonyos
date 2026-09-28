# DRAFT-gzip-hpp-0.1.0-catch1-include-shim

> 草稿：上游测试 `#include <catch.hpp>`（Catch v1 单头风格）在制品仓仅有
> catch2/2.13.10（v2 合并头布局 `catch2/catch.hpp`）时，用 include shim
> 目录转发（不改上游源码、不改上游 CMake）适配。触发自 gzip-hpp 0.1.0
> 适配（2026-09-22）。

## 问题描述

gzip-hpp 0.1.0（mapbox header-only gzip 库）上游测试：

- `test/main.cpp`: `#define CATCH_CONFIG_MAIN` + `#include <catch.hpp>`
- `test/test_io.cpp` / `test/test_version.cpp`: `#include <catch.hpp>` +
  `TEST_CASE`/`SECTION`/`REQUIRE`/`CHECK`/`CHECK_THROWS_WITH(..., Catch::Contains(...))`

上游构建依赖 mason 的 catch 1.9.6（`mason_use(catch VERSION 1.9.6 HEADER_ONLY)`），
制品仓不发布 catch/1.9.6；制品仓可用的 catch2/2.13.10 是 v2 合并头布局：
包内头文件为 `include/catch2/catch.hpp`（不在 include 根，无顶层 `catch.hpp`）。
直接用 `-I <catch2 include根>` 编译上游测试会失败：`'catch.hpp' file not found`。

## 根因

- Catch v1 与 Catch v2 的 include 约定不同：v1 顶层 `catch.hpp`，v2 为
  `catch2/catch.hpp`；上游测试按 v1 约定 include，制品仓只有 v2 包；
- Catch v1 常用 API（TEST_CASE/SECTION/REQUIRE/CHECK/CHECK_THROWS_WITH/
  Catch::Contains）在 v2.13 合并头中全部保留，仅 include 路径不同；
- 因此无需修改上游测试源码，只需让 `catch.hpp` 解析到 v2 合并头。

## 修复（验证通过）

不改上游源码，用 include shim 目录转发：

```bash
mkdir -p shim
cat > shim/catch.hpp <<'EOF'
// Upstream tests use Catch v1 single-header "<catch.hpp>";
// registry provides catch2/2.13.10 (header at catch2/catch.hpp).
#pragma once
#include <catch2/catch.hpp>
EOF
clang++ -std=c++11 -O2 -DNDEBUG \
  -I shim -I <catch2 include根> -I <库 include> -I <zlib include> \
  test/main.cpp test/test_io.cpp test/test_version.cpp <libz.a> -o unit-tests
```

- include 顺序：`-I shim` 在 `<catch2 include根>` 之前，`shim/catch.hpp` 命中
  上游的 `<catch.hpp>`，其内容再 include `<catch2/catch.hpp>`；
- 测试数据相对路径（`./test/data/highly_compressed.gz`）需在源码根目录运行
  可执行文件（cwd 陷阱，非库问题）。

## 验证（真实证据）

- 编译：clang-15 (OHOS aarch64)，exit 0（compile.log）
- 运行（cwd=源码根）：`All tests passed (34 assertions in 7 test cases)`，
  RC=0（run2.log，SHA-256 f0fdf66061feb0fe420a3a9324e257667b3514c57bf104cf5338741d5db4040a）
- 7 个 TEST_CASE 全过；另 2 个 `#ifdef DEBUG` 互斥分支在 Release 未实例化
  （全量 7/9，当前配置可执行集合 7/7）

## 适用边界与反例

- **适用**：上游测试用 Catch v1 风格顶层 `#include <catch.hpp>`（或等效
  单头路径），制品仓只有 catch2 v2.13 合并头布局；测试用到的宏面
  （TEST_CASE/SECTION/REQUIRE/CHECK/CHECK_THROWS_WITH/Catch::Contains）在
  v2.13 合并头中存在。
- **反例**：上游已按 v2 include（`<catch2/catch.hpp>`）→ 直接
  test_requires+CMakeDeps（kangaru 式）；上游用 v3 多头 include
  （catch2/benchmark/... 等）→ 需 cdt 式合并头化 + CMake 修改；上游
  vendored Catch 1.x 且触发 libc++ URNG 静态断言 → mapbox-geometry 式
  幂等补丁（本 shim 不解决 URNG 问题）。
- **边界**：shim 只解决 include 路径；若测试用到 v1 独有、v2 移除的宏，
  shim 方案不适用，需评估 API 差异。

## 查重差异（七轴）

- exact_duplicate: false
- causal_duplicate: false（问题域 = include 布局差异，非同一因果）
- trigger_overlap: true（与 cdt/kangaru 草稿同因：制品仓只有 catch2/2.13.10）
- solution_overlap: 部分（均利用已发布 catch2 包；cdt 改源码 include + CMake，
  kangaru 走 test_requires+CMakeDeps 且上游是 submodule 空目录，本方案是
  纯 include shim 转发、上游源码/CMake 零改动）
- combination_novelty: true（shim 目录 + include 顺序，不触碰上游）
- boundary_novelty: true（明确 v1 单头→v2 合并头的 include 转发边界）
- test_migration_novelty: true（上游测试不改一行即迁移到 v2 并实测全过）

与 DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation：
similar_to（同 catch2 制品仓约束）；与
DRAFT-kangaru-4.3.2-catch2-submodule-test-requires：
similar_to（同 test_requires 场景但方案不同）；无 conflicts_with。
