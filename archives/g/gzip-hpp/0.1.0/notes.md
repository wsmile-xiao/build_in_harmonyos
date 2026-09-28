# gzip-hpp 0.1.0 — 适配笔记

## 基本信息

- 上游：https://github.com/mapbox/gzip-hpp（tag v0.1.0，commit 832d6262cecaa3b85c3c242e3617b4cfdbf3de23）
- 类型：header-only C++11 库（include/gzip/{compress,decompress,config,utils,version}.hpp），无编译产物
- 依赖：zlib（头文件 include <zlib.h>，recipe requires zlib/1.3.2 并经 cpp_info.requires 传递）
- 适配方式：conanfile.py header-library 配方 + test_package 消费者验证 + 上游测试 catch2 shim 适配运行
- 源码修改：**零修改**（无 patches）

## 适配过程与门禁

| 步骤 | 命令 | 结果 |
|---|---|---|
| init-build | ohc-run.py init-build gzip-hpp 0.1.0 | ✅ |
| lang-preflight | ohc-run.py lang-preflight | ✅ cpp |
| conan create | conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 | ✅ test_package PASS |
| 上游测试 | clang++ shim 适配编译 + 源码根运行 | ✅ 7/7, 34 assertions |
| conan-verify | ohc-run.py conan-verify | ✅ G1-G4 PASS |
| finish W3 | ohc-run.py finish (build_and_test.sh) | ✅ L0/L1/L4 pass |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | github.com 直连超时无法下载官方 tarball | 宿主网络限制 | gh-proxy 镜像下载 + 按 sha256 预置 conan sources download_cache（E017/E347 覆盖） |
| 2 | conan create 报 `'settings.os.version' value not defined` | OHOS 适配 conan 对 os.version 的枚举限制 | configure() 中 rm_safe("os.version")（DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe 覆盖） |
| 3 | 上游测试 `#include <catch.hpp>`（Catch v1）无法编译 | 制品仓只有 catch2/2.13.10（v2 合并头 catch2/catch.hpp，无顶层 catch.hpp） | include shim 目录转发，不改上游源码（new_draft，见下） |
| 4 | 上游测试读 `./test/data/highly_compressed.gz` 失败 | 相对路径需从源码根运行 | 运行 cwd 设为源码根，重跑 7/7 通过（非库问题） |
| 5 | finish W3 junk_check 命中其他库基线文件（cloog/kics 的 .staging-verified/.build-closed） | 分支首轮提交前 pr.diff 为空，JC 回退 full 整仓扫描 | 基线隔离：记录 pre SHA-256 (e3b0c44298...)，git rm --cached 临时隔离 → 复跑 W3 pass → git add -f 原样恢复，post SHA-256 一致；当前库 diff 不含该路径 |

## 知识候选台账 + 七轴查重 + 路径决定

任务类型：知识库扩展（路径 B 候选）。

### 候选 1：OHOS conan os.version rm_safe
- 真实错误：`Invalid: 'settings.os.version' value not defined`（conan create）
- 根因：OHOS profile 设 os.version=6.0 且 settings.yml 定义 OHOS version 子设置；配方未声明时 package_id 校验拒绝
- 修复：`configure()` 中 `self.settings.rm_safe("os.version")`
- 验证：conan create / conan-verify G1-G4 全绿
- 四范围查重：正式条目无；草稿 `DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe` 已完整覆盖（问题、根因、修复、验证一致）
- 七轴：exact_duplicate=true（与 glpk 草稿）
- 决定：**reuse_existing**（复用 glpk 草稿知识）

### 候选 2：github 直连超时 → 镜像 + download_cache 预置
- 真实错误：`curl: (28) Failed to connect to github.com port 443 after 20001 ms`（3 次）
- 根因：宿主网络无法直连 github.com；gitcode/cnb 可达
- 修复：gh-proxy 镜像下载官方 tag tarball + 按 sha256 预置 `core.sources:download_cache`（s/<sha256>），conan get 命中缓存
- 验证：conan create 通过；sha256 与官方一致 7ce3908cd13f...
- 四范围查重：正式条目 E017（use-ghfast 镜像）+ E347（pre-seed download cache keyed by sha256）已覆盖
- 七轴：exact_duplicate=true（E017+E347）
- 决定：**reuse_existing**（复用已有正式条目）

### 候选 3：上游 Catch v1 单头 include → catch2/2.13.10 include shim
- 真实错误：`fatal error: 'catch.hpp' file not found`（-I 指向 catch2 v2 包根时）
- 根因：上游测试按 Catch v1 约定 include 顶层 `catch.hpp`；制品仓只有 catch2/2.13.10（v2 合并头 `catch2/catch.hpp`）；v1 常用宏（TEST_CASE/SECTION/REQUIRE/CHECK/CHECK_THROWS_WITH/Catch::Contains）在 v2.13 合并头全部保留，仅 include 路径不同
- 修复：include shim 目录（shim/catch.hpp → `#include <catch2/catch.hpp>`），编译 `-I shim -I <catch2根>`；上游源码/CMake 零改动
- 验证：clang-15 OHOS aarch64 编译 exit 0；源码根运行 `All tests passed (34 assertions in 7 test cases)` RC=0；日志 SHA-256 f0fdf66061feb0fe420a3a9324e257667b3514c57bf104cf5338741d5db4040a
- 四范围查重：
  - 正式条目：无命中（E245/E272/E313 shim 类均为 syscall/tmpfile/stdckdint shim，非 include 转发）
  - 图谱：无
  - 草稿：`DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation`（v3 多头→合并头，改源码+CMake）、`DRAFT-kangaru-4.3.2-catch2-submodule-test-requires`（test_requires+CMakeDeps，submodule 空目录）、`DRAFT-mapbox-geometry-2.0.3-catch1-signed-urng-libcxx-compat-fix`（Catch1 URNG libc++ 断言，非 include 问题）
  - 部分覆盖：cdt/kangaru 同因"制品仓只有 catch2/2.13.10"（trigger_overlap），但方案不同（cdt 改源码 include+CMake；kangaru 走 find_package+test_requires 且上游是 submodule 空目录；本候选是纯 include shim 转发、上游零改动）
- 七轴：
  - exact_duplicate: false
  - causal_duplicate: false
  - trigger_overlap: true（与 cdt/kangaru）
  - solution_overlap: partial（均利用已发布 catch2 包，但手法不同）
  - combination_novelty: true（shim 目录 + include 顺序，不触碰上游）
  - boundary_novelty: true（明确 v1 单头→v2 合并头转发边界与反例）
  - test_migration_novelty: true（上游测试零修改迁移到 v2 并实测全过）
- 关系：similar_to = DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation, DRAFT-kangaru-4.3.2-catch2-submodule-test-requires；无 caused_by/prerequisite_of/conflicts_with
- 决定：**new_draft**（路径 B）— 已建 `knowledge/drafts/DRAFT-gzip-hpp-0.1.0-catch1-include-shim.{md,kv}`

### 路径决定汇总

| 候选 | 决定 | 依据 |
|---|---|---|
| 1 os.version rm_safe | reuse_existing | glpk 草稿完整覆盖 |
| 2 github 超时/下载缓存 | reuse_existing | E017+E347 正式条目覆盖 |
| 3 catch1 include shim | new_draft (路径 B) | 部分覆盖但有已验证的新增差异，可跨库复用 |

最终路径：**B（知识库扩展）** — new_draft 且 .md/.kv 配对，PR 前缀【知识库扩展】。
