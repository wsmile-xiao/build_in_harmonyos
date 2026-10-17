# orcania 2.3.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: {2026-09-16}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 上游测试枚举台账（R51，源码声明口径）

官方 tag v2.3.2 测试清点（tar 内 `test/` 与 CMakeLists 注册）：

| 测试源 | START_TEST 声明数 | tcase_add_test 注册数 | 分类 | 说明 |
|--------|-------------------|----------------------|------|------|
| test/str_test.c | 34 | 34 | 独立上游用例 | 字符串操作（strdup/strcat/strcmp/startswith/endswith/strnul/str_trim/str_replace 等） |
| test/pointer_list_test.c | 11 | 11 | 独立上游用例 | pointer_list 增删改查/释放 |
| test/split_test.c | 4 | 4 | 独立上游用例 | split_string/string_array_has_value/join/size |
| test/memory_test.c | 2 | 2 | 独立上游用例 | o_malloc/o_realloc |
| test/run_test.sh | - | - | 非用例（包装脚本） | 仅调用各测试二进制，不新增用例 |

- 独立上游用例总数：34+11+4+2 = **51**
- CTest 注册：str_test/split_test/memory_test/pointer_list_test 四个 `add_test`（CMakeLists.txt，BUILD_ORCANIA_TESTING=ON 时）
- 测试框架：Check（`find_package(Check)`，必需）+ Subunit（`find_package(Subunit REQUIRED)`，非 WIN32/APPLE 时硬性要求）
- 源码统计：src/ 3 个 C（base64.c 341 行 / memory.c 59 行 / orcania.c 679 行），include/orcania.h 685 行，共 8 个 C 源文件
- CLI：BUILD_BASE64URL=ON（默认）→ 构建并 install `base64url` 可执行（R38：需要 commands.json）
- 版本核对：CMakeLists 中 LIBRARY_VERSION=2.3.2，与任务一致

## 依赖版本
- 运行时：仅 libc（无外部依赖）
- 测试：check（libcheck）+ subunit（仅测试构建期；OHOS 上 check/0.15.2 为自包含 libcheck，见 2.3.3 归档 patch 0001）

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 验证结果

### 上游测试实测（双口径台账）

CTest 4/4 通过，4 个官方测试程序内 51 个用例全部实际运行并通过：

| 测试程序 | 源码声明 (START_TEST) | 实际执行通过 | ctest 注册 |
|----------|----------------------|--------------|-----------|
| str_test | 34 | 34 | Test #1 Passed |
| split_test | 4 | 4 | Test #2 Passed |
| memory_test | 2 | 2 | Test #3 Passed |
| pointer_list_test | 11 | 11 | Test #4 Passed |
| **合计** | **51** | **51** | **4/4** |

- `source_declared_total` = 51（str_test 34 + pointer_list_test 11 + split_test 4 + memory_test 2，均为 `START_TEST`+`tcase_add_test` 双登记）
- `executed_passed_total` = 51，全量通过率 **51/51 = 100%**
- 未实例化/未注册：0 项（CMakeLists 显式注册全部 4 个程序，无互斥分支）
- 依赖恢复：check/0.15.2（conan cache）提供 Check 头/lib，patch 0001 使 Subunit 可选；TMPDIR 指向可写 `.test-tmp`（libcheck fork IPC）
- 运行命令：`ctest --test-dir build --output-on-failure`（exit 0），日志 /storage/Users/currentUser/tmp/orcania-2.3.2-ctest.log

### r02 复跑（2026-09-17，代码审查返工后）

修复 conandata.yml URL 与 ohos_special_test.c（原子化 + 泄漏修复）后全量复跑：

- CTest 4/4 通过（exit 0），日志 /storage/Users/currentUser/tmp/orcania-2.3.2-r02-ctest.log
- 各程序实际执行用例数：str_test 34 + split_test 4 + memory_test 2 + pointer_list_test 11 = **51/51 (100%)**，与 r01 基线一致，未静默改动声明总数
- 统计口径：source_declared_total=51 / configured_executable_total=4（ctest）/ executed_passed_total=51 / failed=0 / uninstantiated=0

```bash
$ ctest --test-dir /storage/Users/currentUser/tmp/builds/orcania-2.3.2.work/build --output-on-failure
100% tests passed, 0 tests failed out of 4
```

## 注意事项
- GitHub 直连超时，tarball 经 ghfast.top 镜像下载；SHA-256=fcd93c554afeb694a36ac3c8bd1fa767028b373cb0b94a9396124c4e36d24038，conandata.yml 必须写官方 https 源
- 2.3.3 归档已有同类适配（patch 0001-ohos-subunit-optional.patch），2.3.2 应先核对同源 patch 是否可直接复用

## 知识候选台账（knowledge_candidate_ledger）

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 查重结果 |
|---|------|----------|------|------|------|----------|----------|
| KC1 | OHOS CMake+Check 库上游测试启用：Subunit 硬依赖可选化 + FindCheck 种子注入 | `find_package(Subunit REQUIRED)` 在 OHOS 上找不到（conan libcheck 自包含，无 Subunit 制品）→ CTest 树无法构建 | OHOS 无独立 Subunit 包；libcheck（check/0.15.2）已自包含，上游 CMake 却硬性要求 Subunit | patch：`find_package(Subunit)` 去 REQUIRED + `if(SUBUNIT_FOUND)` 条件链接；conanfile 注入 `CHECK_INCLUDE_DIR`/`CHECK_LIBRARY`，不用 CMakeDeps（CONFIG 模式会让上游 FindCheck 模块守卫失效） | W3/conan-verify G2 通过，CTest 4/4、51/51 用例通过 | 任何 OHOS 上以 CMake+Check 为测试框架的 C 库 | 知识库无 orcania/subunit 条目；E515(strip)、E547(P_tmpdir)、E321(header-only) 均不覆盖 → 未命中 |
| KC2 | finish refresh-patch 重命名导致 conandata.yml 补丁引用失效 | conan create `export_sources` 报 `Patch file does not exist: .../0001-ohos-subunit-optional.patch` | finish [1/10] refresh-patch --auto 按 tracker 将补丁重命名为 `0001-CMakeLists.txt.patch` 并备份旧名，conandata.yml 仍引用旧名 | 将 conandata.yml `patch_file` 更新为 refresh-patch 实际生成的文件名，删除 `.patch-backup-*` | 重跑 finish W3/G2 通过 | 任何带 patches/ 且被 finish 重新生成的库 | 知识库无此触发点条目；E254/E484(dry-run 污染)、E515(strip)、libstatgrab(未声明)、celero(export hook) 均不同 → 未命中 → **new_draft** |

### 七轴查重（针对 KC1 主候选）

- `exact_duplicate`: false（知识库无 orcania/subunit/FindCheck 种子注入条目）
- `causal_duplicate`: false（E547 根因是 P_tmpdir 优先、E515 是 strip 参数，均与 Subunit 硬依赖无关）
- `trigger_overlap`: partial（E515 同为 refresh-patch/conandata patches 工具链，但触发点是 strip 而非依赖缺失）
- `solution_overlap`: partial（E515 改 strip 参数；本候选是去 REQUIRED + 条件链接 + FindCheck 种子，方案不同）
- `combination_novelty`: true（"Subunit 可选化 + FindCheck 模块种子注入 + 禁用 CMakeDeps 避免 CONFIG 模式守卫失效"三组合无既有条目）
- `boundary_novelty`: true（适用边界明确：仅当 libcheck 自包含、测试程序只用 check.h 时；若测试用 subunit API 则不能去）
- `test_migration_novelty`: false

### 路径决定

- KC1 已验证、可跨库复用（libwbxml 同模式先例 + 2.3.3 复用同 patch）、查重未命中 → **new_draft（路径 B）**，建立同 stem 的 .md/.kv 草稿
- 关系：`similar_to` E515/E547（同为 OHOS 测试环境/补丁工具链类）；`caused_by` OHOS 无独立 Subunit 制品；`conflicts_with` 无；`prerequisite_of` 无
- 复用结论：`reuse_existing` 不适用（无既有条目）；`new_draft` = KC1 主候选；`path_a_no_knowledge` = false（存在新增知识价值）
---

**编译结束**: 2026-09-17 10:07
**最终状态**: built
