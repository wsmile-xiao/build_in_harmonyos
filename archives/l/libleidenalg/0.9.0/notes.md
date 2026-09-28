# libleidenalg 0.9.0 适配笔记

## 编译环境

- 构建系统: cmake（上游要求 >= 3.23）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built
- 上游版本: 0.9.0（GitHub tags `v0.9.0`，C++ 库 CMake 布局；
  注意同仓库另有同名 `0.9.0` 无前缀 tag 指向 Python 打包时代布局，勿用）
- 上游仓库: https://github.com/vtraag/libleidenalg
- 源码包: https://github.com/vtraag/libleidenalg/archive/refs/tags/v0.9.0.tar.gz
- 源码 SHA256: `ab54651234e4c3b89727b5e6a7b4a8285430ed8326c59d95d45adbb5836268aa`

## 编译步骤

CMake 标准流程，依赖由 Conan 提供：

```bash
conan create archives/l/libleidenalg/0.9.0 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方基于同库 0.13.0 已验证配方（编译器存在性门控、HMBS 只读 /tmp 修复、
igraph include 补偿、CMakeDeps/CMakeToolchain），按 0.9.0 特点调整：
`requirements() igraph/1.0.0`（transitive_headers/libs），
`build()` 依次 `cmake.configure()` + `cmake.build()`，
`package()` 复用 `cmake.install()` 并附带 LICENSE，
`package_info()` 声明 `libs=["libleidenalg"]`、`requires=["igraph::igraph"]`、
`cmake_target_name=libleidenalg::libleidenalg`、
`includedirs=["include","include/libleidenalg"]`（见问题 #4）、
`system_libs=["m"]`（Linux/OHOS）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create configure 失败：`find_package(igraph 0.10 CONFIG REQUIRED)` 报 "Could not find a configuration file for package igraph that is compatible with requested version 0.10"，候选 igraph-config.cmake version 1.0.0 被拒 | CMakeDeps 生成的 igraph-config-version.cmake 采用"同主版本"兼容校验（PACKAGE_FIND_VERSION_MAJOR STREQUAL CVF_VERSION_MAJOR）：请求 0.10 的 major=0 与 igraph 1.0.0 的 major=1 不匹配，即使 1.0.0 > 0.10 也判不兼容 | patches/0001-CMakeLists.txt.patch：去掉 find_package 的版本下限 `0.10` → `find_package(igraph CONFIG REQUIRED)`（0.9.0 实际只用 igraph 1.x 稳定 API，编译与测试实证兼容） |
| 2 | G2 编译失败：`GraphHelper.cpp:452: error: no matching function for call to 'igraph_incident'`（4 参）与 `igraph_neighbors`（4 参） | igraph 1.0 对这两个接口做了签名扩展：`igraph_neighbors` 6 参（新增 loops、multiple），`igraph_incident` 5 参（新增 loops）；0.10 时代 4 参调用不再匹配 | patches/0003-src-GraphHelper.cpp.patch：按 igraph 1.0 官方迁移语义适配——`igraph_incident(g,e,v,mode,IGRAPH_LOOPS_TWICE)`、`igraph_neighbors(g,n,v,mode,IGRAPH_LOOPS_TWICE,true)`，等价保留 0.10 环计数语义 |
| 3 | test_package 编译失败：`CPMVertexPartition.h:4: fatal error: 'LinearResolutionParameterVertexPartition.h' file not found` | 上游 include/CMakeLists.txt 的 `FILE_SET headers` 漏列 `LinearResolutionParameterVertexPartition.h`（源码树 11 个头文件只装 10 个）；且 0.9.0 公开头互相用尖括号同级包含（`CPMVertexPartition.h` 内 `#include <LinearResolutionParameterVertexPartition.h>`），消费者仅带 `-I<prefix>/include` 找不到 `include/libleidenalg/` 下的同级头 | 双管齐下：patches/0002-include-CMakeLists.txt.patch 把漏头补进 FILE_SET；主配方 `package_info()` `includedirs=["include","include/libleidenalg"]`，CMakeDeps 目标同时携带 `<prefix>/include` 与 `<prefix>/include/libleidenalg` |
| 4 | W3 本地 CI 模拟 JC 门禁误报：junk_check full 模式检出 `archives/c/cloog/0.21.1/.build-closed`、`.staging-verified` 与 `archives/k/kics/2.1.20/.staging-verified` | 这 3 个空状态文件是 main 上其他库历史 PR（cloog/kics）已跟踪的基线 junk（blob e69de29），不属于本库允许范围 | 按 Skill 基线隔离规则：临时 `git rm --cached` 移出 index → 复验 W3（JC 通过，100%）→ 用 `git add -f` 无条件恢复原 blob，确认与 main 零差异；未提交、未删除、未纳入本库 diff |

## 源码修改

- patches/0001-CMakeLists.txt.patch：find_package 去版本下限（CMakeDeps 同主版本闸绕行）
- patches/0002-include-CMakeLists.txt.patch：FILE_SET 补 LinearResolutionParameterVertexPartition.h
- patches/0003-src-GraphHelper.cpp.patch：igraph_neighbors/igraph_incident 适配 igraph 1.x 签名

## 依赖版本

- igraph/1.0.0（仓内已归档 `archives/i/igraph/1.0.0`，CMakeDeps 提供 `igraph::igraph`；制品仓已发布）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify libleidenalg 0.9.0
# G0-G5 全通过；test_package ./test_leidenalg 6/6 PASS：
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"./test_leidenalg","discovered":6,"passedCount":6}
# HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","discovered":0,...}（上游无自动化测试，见 MANIFEST.yml 审计）

python3 scripts/ohc-run.py finish libleidenalg 0.9.0 built
# W3 本地 CI 模拟（build_and_test.sh）1/1 100%：JC pass / L0 pass / L1 pass / L2 skip(无bin) / L4 pass / L5 pass
```

## 注意事项

- 上游 `0.9.0`（无前缀）tag 是 Python 打包时代布局（setup.py + vendored igraph），
  本库 C++ 库正式标签为 `v0.9.0`；conandata.yml 已用 `v0.9.0`，勿混淆。
- 知识判定：路径 B（无等价命中 + 跨库可复用），草稿对
  `knowledge/drafts/DRAFT-libleidenalg-0.9.0-igraph-1.0-api-migration.{md,kv}`。
- W3 JC 误报的 3 个基线文件已精确恢复，本 PR 不含任何基线/框架/其他库改动。

---

**编译结束**: 2026-09-23
**最终状态**: built
