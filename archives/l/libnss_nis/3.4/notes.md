# libnss_nis 3.4 — HarmonyOS PC 适配笔记

## 概述

libnss_nis 是 Thorsten Kukuk 维护的 glibc NSS（Name Service Switch）模块，
通过 NIS/YP 协议提供 passwd/group/host/netgroup/alias/rpc 等数据库查询，
以 `libnss_nis.so.2` 形式被 glibc NSS 框架 dlopen() 加载。

- 官方源: https://github.com/thkukuk/libnss_nis/releases/download/v3.4/libnss_nis-3.4.tar.xz
- SHA-256: `ee237a957c5f07d8bc3cf245f56537697cc4e1d7d1bfe4a814e48f825764b6ee`（下载实测一致）
- 构建系统: Autotools（configure + make，libtool）
- 平台: HarmonyOS PC aarch64 / musl libc / clang 15（原生编译，非交叉）
- 消费者: NSS 框架 dlopen 加载，业务层经 dlsym 解析 `_nss_nis_*_r` 符号

## 适配要点（3 项平台差异）

### 1. glibc 专有头缺失（patches/0001-ohos-glibc-compat-headers.patch）

OHOS/musl 没有 glibc 专有的三个头，libnss_nis 源码无条件 include 它们：
`<nss.h>`、`<aliases.h>`、`<rpc/netdb.h>`。补丁在 `src/` 下新增三个最小兼容头
（`src/Makefile.am` 的 `AM_CPPFLAGS = -I$(srcdir)` 使编译时解析到树内文件）：

- `src/nss.h`：`enum nss_status` + `NSS_STATUS_TRYAGAIN/UNAVAIL/NOTFOUND/SUCCESS/RETURN`
  （布局对齐 glibc nss/nss.h）；`gethostbyname4_r` NSS 接口需要的
  `NETDB_INTERNAL`/`NETDB_SUCCESS` 与 `struct gaih_addrtuple`
  （布局对齐 glibc inet/getaddrinfo.h）；`__mempcpy` → `mempcpy` 宏映射。
- `src/aliases.h`：`struct aliasent`（nis-alias.c 用到
  alias_name/alias_members/alias_members_len/alias_local，布局对齐 glibc inet/aliases.h）。
- `src/rpc/netdb.h`：rpc 模块只用到 `struct rpcent`（由 libtirpc 的
  `<rpc/rpcent.h>` 提供），该头仅转发包含 rpcent.h。

不修改任何 .c 文件。musl 导出 `mempcpy()` 但无 glibc 内部名 `__mempcpy`，
编译期由宏映射解决（nis-pwd.c 4 处调用）。

### 2. config.guess 不识别 HarmonyOS

`uname -s = HarmonyOS` 时 config.guess 报
`cannot guess build type; you must specify one`。显式指定原生 GNU triplet
`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
完全跳过 config.guess/config.sub（与 libnsl/2.0.1、classads/1.0.10 先例一致）。

### 3. RPC/NIS 依赖来自 conan 制品仓

NIS(YP) 客户端 API（yp_match/yp_first/yp_get_default_domain/...）与
`rpcsvc/yp*.h` 由 libnsl 提供，TI-RPC 原语（rpc/rpc.h 等，安装于
include/tirpc/）由 libtirpc 提供，两者均已发布：
- requires `libnsl/2.0.1`（其内部 requires libtirpc/1.3.7）
- `PkgConfigDeps` 生成 libnsl.pc/libtirpc.pc → `PKG_CONFIG_PATH` 指向
  generators 目录 → configure 的 `PKG_CHECK_MODULES([TIRPC]/[LIBNSL])` 命中

configure.ac 中 libtirpc 与 libnsl 的 PKG_CHECK 均带 `[]` 空回退，但源码
无条件 include rpc 头并链接 `-lnsl -ltirpc`，因此配方中为硬 requires。

## 其他配方细节

- HMDFS/setgid 兼容：configure 临时目录 umask 077 → 022
  （同 libnsl/2.0.1、gmime/3.0.6 处理），否则 config.status 报
  `Permission denied`。
- `CONFIG_SHELL=/bin/sh`：避免 autoconf 重 exec 到 bash 后在 hmfs 上
  getcwd 失败（同 libnsl/2.0.1 的 DRAFT-E551/DRAFT-6487 教训）。
- `package_info.includedirs = []`：NSS 模块不安装公共头文件；conan 默认
  cpp_info 声明 `${pkg}/include`，CMakeDeps 会生成指向不存在路径的
  INTERFACE_INCLUDE_DIRECTORIES，导致 test_package find_package 报
  "includes non-existent path"。
- 默认 `shared=True`（NSS 模块按 dlopen 消费，与 nss-wrapper 一致）。
- 禁止动态链接系统同名库规则（R26）不适用：OHOS 系统无 libnss_nis。

## 上游测试台账（完整枚举）

| 项 | 位置 | 独立上游用例? | 实际运行 | 结果 |
|---|---|---|---|---|
| nss_loader-test | src/nss_loader-test.c（check_PROGRAMS=TESTS） | 是（唯一） | make check | PASS |

- `make -n check` 分析：`check_PROGRAMS = nss_loader-test`，
  `TESTS = $(check_PROGRAMS)`，仅此 1 个独立用例。
- 源码中 `#if 0` 内的实际 NIS 查询被上游禁用，测试仅验证
  dlopen(".libs/libnss_nis.so.2") + dlsym("_nss_nis_getpwnam_r")。
- OHOS 实测：`PASS: nss_loader-test`（TOTAL 1 / PASS 1，见 conan-create.log）。
- 框架内部宏（NSS_STATUS_*、libc-symbols.h 别名宏等）不计入用例。

## 双口径统计

- source_declared_total = 1（src/Makefile.am TESTS 唯一声明）
- configured_executable_total = 1（当前配置实例化的 nss_loader-test）
- executed_passed_total = 1，失败 0，未运行 0
- 通过率：1/1 (100%)，全量口径与执行口径一致

## test_package（消费者验证）

`test_package/test.c` 模拟业务层 NSS 使用者：
1. `dlopen("libnss_nis.so.2", RTLD_NOW)` — 模块产物可加载
2. `dlsym("_nss_nis_getpwnam_r")` — 公开 API 符号可解析
3. 实际调用 `_nss_nis_getpwnam_r` — OHOS 无 NIS 域配置，
   断言返回 NSS_STATUS_UNAVAIL（可观察结果，验证入口可执行且行为正确）

CTest 实测 `1/1 Test #1: test_libnss_nis ... Passed`（conan-create.log）。

## 验证记录

- 手动编译验证：configure（显式 triplet + compat CPPFLAGS）→ make → make check 全过
- conan create（干净构建）：G2 PASS（含 test_package 消费者测试执行通过）
- conan-verify：G0/G1/G2/G3/G4 全 PASS

## 未完成项 / 已知限制

- NSS 模块仅可在存在 NSS 框架的 libc 上被系统消费；OHOS 目前无 NIS 域
  与 NSS 框架运行时消费场景，交付以模块产物 + 消费者自测为准。
---

**编译结束**: 2026-09-23 04:18
**最终状态**: published

## 知识候选台账（knowledge_candidate_ledger）

| # | 候选（非噪声） | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 四范围查重 | 判定 |
|---|---------------|----------|------|------|------|----------|-----------|------|
| 1 | glibc NSS 专有头（nss.h/aliases.h/rpc/netdb.h）在 OHOS/musl 缺失 | `fatal error: 'nss.h' file not found`（nis-*.c 10 个文件）；随后暴露 `NETDB_INTERNAL`/`struct gaih_addrtuple`/`__mempcpy` | libnss_nis 是 glibc NSS 模块，无条件 include glibc 内部头；OHOS musl libc 无 NSS 框架与这些头 | patches/0001 在 src/ 树内新增最小兼容头：nss.h（enum nss_status + NSS_STATUS_* + NETDB_INTERNAL/NETDB_SUCCESS + struct gaih_addrtuple + __mempcpy→mempcpy 映射）、aliases.h（struct aliasent）、rpc/netdb.h（转发 rpcent.h）；-I$(srcdir) 自然解析 | make PASS；make check 1/1 PASS；conan create G2 PASS；消费者 dlopen+dlsym+实际调用 PASS | 任何依赖 glibc NSS 基础设施头的库（libnss_* 家族、NSS 模块），可跨库复用 | 正式 E 条目无命中（E544-draft 仅覆盖 NETDB_INTERNAL 宏；E020 是 FILE 内部字段；E194 是 bits/alltypes.h 且 forbid 复制 glibc 头——本方案是树内最小声明非复制）；graph 无；drafts 部分覆盖 | **路径 B**（new_draft） |
| 2 | NSS 模块无公共头文件时 cpp_info.includedirs 需清空 | test_package find_package 报 `includes non-existent path .../p/include` | Conan 默认 cpp_info.includedirs=include，CMakeDeps 生成指向不存在目录的 INTERFACE_INCLUDE_DIRECTORIES | package_info() 中 `self.cpp_info.includedirs = []` | conan create G2 PASS（test_package 编译链接运行全过） | 任何不安装公共头文件的库配方（headerless library） | **E498 完全覆盖**（formal，explicit-empty-public-include-contract） | **路径 A**（reuse_existing） |
| 3 | config.guess 不识别 HarmonyOS（uname -s=HarmonyOS） | `configure: error: cannot guess build type; you must specify one` | GNU config.guess 无 HarmonyOS 分支 | 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（原生 triplet）跳过猜测 | configure PASS → make → make check → conan create 全链 PASS | 所有 autotools 项目（鸿蒙第一道门槛） | **E007/E072 完全覆盖**（E007 即 cannot guess build type；E072 是 config.sub ohos 三元组） | **路径 A**（reuse_existing） |
| 4 | HMDFS/setgid 下 configure 临时目录 umask 077 | `config.status[NNNN]: can't create ./confXXXXXX/subs1.awk: Permission denied` | hmfs/hmdfs 上 0700 目录对下一进程不可写 | configure 脚本 umask 077→022（配方内 replace_in_file） | conan create PASS | 所有在 hmfs/hmdfs 跑 autotools configure 的库 | **已有 DRAFT-E551/DRAFT-6487 覆盖**（gmime/classads/libnsl 同处理） | **路径 A**（reuse_existing） |

### 七轴查重（候选 1 详细）

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | false | 无完整重复条目（E544 只含 NETDB_INTERNAL 一项，无 nss.h/aliases.h/gaih_addrtuple/__mempcpy） |
| causal_duplicate | false | 根因不同：E544 是 musl netdb 宏缺项，本候选是 glibc NSS 框架头整体缺失 |
| trigger_overlap | partial | 编译期 `undeclared identifier`/`file not found` 触发面与 E544 部分重叠（NETDB_INTERNAL） |
| solution_overlap | partial | E544 用 `#ifndef NETDB_INTERNAL` fallback；本候选是树内完整最小声明头 + 符号映射，范围更广 |
| combination_novelty | true | nss.h+aliases.h+rpc/netdb.h+gaih_addrtuple+__mempcpy 组合此前无条目 |
| boundary_novelty | true | 明确"树内最小声明头 ≠ 复制 glibc 头"边界（E194 forbid 复制到 musl，本方案守界） |
| test_migration_novelty | true | NSS 模块消费者 dlopen+dlsym+实际调用返回 NSS_STATUS_UNAVAIL 的验证方法无先例 |

关系: similar_to=E544-draft（NETDB_INTERNAL 宏）、E194（glibc 头边界）；caused_by=musl 无 glibc NSS 基础设施；
prerequisite_of=libnss_nis 系列模块；conflicts_with=E194 的 forbid（仅当复制 glibc 头到系统 include 时，本方案不冲突）。

### 路径判定

**路径 B（知识库扩展）**，`new_draft`：候选 1 已验证、可跨库复用（任何 NSS 模块/glibc 专有头依赖库）、
查重部分覆盖且存在新增差异；候选 2/3/4 复用既有知识（E498/E007/E072/DRAFT-E551）。
草稿对：knowledge/drafts/DRAFT-libnss_nis-3.4-glibc-nss-compat-headers.{kv,md}（同 stem 配对）。
