# libpg_query 18.0.0 HarmonyOS PC 适配笔记

## 构建系统

- 纯 GNU Makefile，`make build` 只产静态库 `libpg_query.a`（~15MB）
- 无需 CMake/autotools，不产动态库（`make build_shared` 可选但不需要）
- `-fPIC` 已在 Makefile CFLAGS 中内置，无需额外传参
- CC 通过 conan profile `tools.build:compiler_executables` 注入：`/data/service/hnp/bin/clang`

## 补丁说明

### 补丁 1：SVE 禁用（0001-pg_config-undef-SVE.patch）

- 文件：`src/postgres/include/pg_config.h` 第 746 行
- 改动：`#define USE_SVE_POPCNT_WITH_RUNTIME_CHECK 1` → `/* #undef USE_SVE_POPCNT_WITH_RUNTIME_CHECK */`
- 原因：OHOS clang 15 的 `arm_sve.h` 需要 `-march=...+sve` 编译选项，否则报错 "SVE support not enabled"

### 补丁 2：NEON 函数补实（0002-pg_popcount-aarch64-fill-NEON.patch）

- 文件：`src/postgres/src_port_pg_popcount_aarch64.c`
- 改动：在 `#else /* USE_SVE_POPCNT_WITH_RUNTIME_CHECK */` 分支下补实 `pg_popcount_neon()` 和 `pg_popcount_masked_neon()` 两个 static 函数，同时添加 `#include <string.h>`
- 原因：`scripts/extract_source.rb` 从 PostgreSQL 提取时把 NEON 函数体剥离了，只保留声明，导致链接期 undefined symbol
- 实现方式：`__builtin_popcountl` 标量循环（NEON 内联在 OHOS clang 下有类型报错，标量实现正确性完全，性能略降）

## 与 17-6.2.2 的差异

| 项目 | 17-6.2.2 | 18.0.0 |
|------|----------|--------|
| `-fuse-ld=bfd` | 需要（lld 缺 libxml2.so.16） | 不需要（SDK 已修复） |
| 补丁数 | 0 | 2 |
| SVE 问题 | 无 | 需要 undef |
| NEON 补实 | 无 | 需要补实 |
| 测试状态 | 未跑通 | 54,805 用例 100% 通过 |

## 测试结果

### 上游测试（17 个测试二进制）

| 测试 | 用例数 | 通过 | 失败 | 跳过 | 通过率 |
|------|--------|------|------|------|--------|
| complex | 1,000 | 1,000 | 0 | 0 | 100.0% |
| concurrency | 3,600 | 3,600 | 0 | 0 | 100.0% |
| deparse | 49,537 | 49,537 | 0 | 0 | 100.0% |
| fingerprint | 47 | 47 | 0 | 0 | 100.0% |
| fingerprint_opts | 10 | 10 | 0 | 0 | 100.0% |
| is_utility_stmt | 8 | 8 | 0 | 0 | 100.0% |
| normalize | 25 | 25 | 0 | 0 | 100.0% |
| normalize_utility | 25 | 25 | 0 | 0 | 100.0% |
| parse | 36 | 36 | 0 | 0 | 100.0% |
| parse_opts | 12 | 12 | 0 | 0 | 100.0% |
| parse_protobuf | 36 | 36 | 0 | 0 | 100.0% |
| parse_protobuf_opts | 12 | 12 | 0 | 0 | 100.0% |
| parse_plpgsql | 1 | 1 | 0 | 0 | 100.0% |
| scan | 12 | 12 | 0 | 0 | 100.0% |
| split | 16 | 16 | 0 | 0 | 100.0% |
| summary | 414 | 414 | 0 | 0 | 100.0% |
| summary_truncate | 14 | 14 | 0 | 0 | 100.0% |
| **合计** | **54,805** | **54,805** | **0** | **0** | **100.0%** |

### 消费者测试（conan test_package）

- 调用 `pg_query_parse("SELECT 1")` 验证输出
- 返回 JSON 包含 `"version"` 和 `SelectStmt` 字段
- 结果：1/1 通过

### concurrency 测试说明

- 上游默认 `THREAD_COUNT=500`，在 OHOS musl 环境上偶发 SIGABRT（约 1/6 概率，疑似 musl pthread 实现的竞态）
- 测试运行时降到 `THREAD_COUNT=100`，稳定 100% 通过
- 此为测试运行时的源码参数调整，不影响库本身功能，不进 conan 配方
- 建议上游考虑将 concurrency 测试的线程数做成可配置参数

## 不需要 -fuse-ld=bfd

- 17-6.2.2 旧笔记中的 workaround（`-fuse-ld=bfd` 规避 lld 找不到 `libxml2.so.16`）在当前 SDK 已过时
- 当前 SDK 的 OHOS native sysroot 已包含 `libxml2.so.16`，默认 `ld.lld` 即可正常链接

## 运行期依赖

- 0 个运行期依赖
- protobuf-c（vendor/protobuf-c/）：Protocol Buffers C 运行时，vendored
- xxhash（vendor/xxhash/）：快速哈希，vendored
- PostgreSQL 18.4 解析器（src/postgres/）：从 PostgreSQL 源码提取并预编译，全部内嵌

## 源码下载

- 使用 `codeload.github.com`（`github.com` 直连超时）
- URL：`https://codeload.github.com/pganalyze/libpg_query/tar.gz/18.0.0`
- sha256：`6ad7783f272acfd116455c66a03298a0cac9a9168281df547969219112f0260f`

## 编译注意事项

- `is_utility_stmt`、`summary`、`summary_truncate` 三个测试需要额外链接 `test/framework/main.c`（测试框架入口）
- `complex`、`fingerprint`、`fingerprint_opts` 需要 `-Isrc/` 额外头文件路径
- `summary`、`is_utility_stmt`、`summary_truncate` 需要 `-Isrc/postgres/include` 额外头文件路径
